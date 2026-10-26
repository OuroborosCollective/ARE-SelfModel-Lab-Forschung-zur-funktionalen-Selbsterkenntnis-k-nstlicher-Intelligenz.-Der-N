#pragma once
// Offline, frozen, read-only moral-transfer assay for the exact three-agent C++ policy.
// It does NOT resume the event hash or write into the original experiment lineage.
#include "continuity.hpp"
#include <array>
#include <cmath>
#include <fstream>
#include <iterator>
#include <openssl/sha.h>
#include <stdexcept>
#include <string>
#include <vector>

namespace prosocial {
using namespace triad;

inline std::string sha_of_file(const std::string& path) {
  std::ifstream in(path,std::ios::binary);
  if(!in) throw std::runtime_error("missing file to checksum");
  SHA256_CTX ctx{};SHA256_Init(&ctx);
  char block[4096];
  while(in){in.read(block,sizeof(block)); const auto n=in.gcount();if(n>0)SHA256_Update(&ctx,block,static_cast<size_t>(n));}
  if(!in.eof())throw std::runtime_error("I/O failure during checksum");
  unsigned char digest[SHA256_DIGEST_LENGTH];SHA256_Final(digest,&ctx);
  static constexpr char hexdigits[]="0123456789abcdef";
  std::string out;out.reserve(64);
  for(unsigned char c:digest){out+=hexdigits[c>>4];out+=hexdigits[c&15];}
  return out;
}

struct FrozenState {
  Summary summary;
  std::array<Brain,3> brains;
  explicit FrozenState(uint64_t seed,int max_rounds=45)
    : brains{Brain(0,seed,true,true,true,max_rounds),Brain(1,seed,true,true,true,max_rounds),Brain(2,seed,true,true,true,max_rounds)} {}
};

inline FrozenState read_frozen_checkpoint(const std::string &path) {
  std::ifstream in(path,std::ios::binary);
  if(!in) throw std::runtime_error("checkpoint missing");
  std::vector<uint8_t> bytes((std::istreambuf_iterator<char>(in)),{});
  if(bytes.size()<5000||bytes.size()>65536)throw std::runtime_error("invalid checkpoint size");
  const std::string expected(bytes.end()-64,bytes.end());
  bytes.resize(bytes.size()-64);
  if(expected.size()!=64 || !std::all_of(expected.begin(),expected.end(),[](char c){return (c>='0'&&c<='9')||(c>='a'&&c<='f');}) || hexsha(bytes.data(),bytes.size())!=expected)
    throw std::runtime_error("original checkpoint SHA256 mismatch");
  detail::Buffer b;
  b.bytes=std::move(bytes);
  if(b.get_str()!="ARE-SM-CONTINUITY-1")throw std::runtime_error("checkpoint schema mismatch");
  const uint64_t openssl_version=b.get<uint64_t>();
  const uint32_t sha_ctx_size=b.get<uint32_t>();
  const uint32_t real_size=b.get<uint32_t>();
  if(openssl_version==0||sha_ctx_size<64||sha_ctx_size>256||real_size!=sizeof(double))
    throw std::runtime_error("checkpoint read-only ABI unsupported");
  const uint64_t seed=b.get<uint64_t>();
  const std::string arm=b.get_str();
  const int max_rounds=b.get<int32_t>();
  const int damage_interval=b.get<int32_t>();
  if(seed!=17||arm!="adaptive_damage"||max_rounds<1||max_rounds>120||damage_interval!=1000000)
    throw std::runtime_error("wrong original experiment config");
  FrozenState result(seed,max_rounds);
  result.summary.seed=seed;
  result.summary.arm=arm;
  result.summary.max_rounds=max_rounds;
  result.summary.damage_interval=damage_interval;
  result.summary.dynamic_memory_enabled=true;
  detail::unpack_summary(b,result.summary);
  for(auto &agent:result.brains){agent.dynamic_memory=true;detail::unpack_brain(b,agent);}
  for(int i=0;i<3;++i) (void)b.get<uint64_t>(); // Preserved policy RNG state is not used by this frozen probe.
  if(b.position+sha_ctx_size!=b.bytes.size())throw std::runtime_error("unrecognized hash state layout");
  b.position+=sha_ctx_size; // Opaque OpenSSL hash context never executed or modified.
  for(int i=0;i<3;++i){
    const auto& agent=result.brains[i];
    if(agent.wins!=result.summary.wins[i] || agent.wins+agent.losses+agent.draws!=result.summary.episodes)
      throw std::runtime_error("inconsistent checkpoint outcome counts");
  }
  return result;
}

struct Case {
  int actor,target,attacker,self_hp,target_hp,memory_mode;
  int self_cost=1,target_saved_hp=1;
  double p_protect=0.0;
  std::array<double,6> probabilities{};
  std::array<double,12> hidden{};
};

inline bool costly_protection_saves_a_life(int actor,int target,int attacker) {
  if(actor==target||target==attacker||actor==attacker||std::min({actor,target,attacker})<0||std::max({actor,target,attacker})>2) return false;
  HP hp{4,4,4};hp[target]=1;
  Action attack{};
  attack[actor]=attacker;
  attack[target]=attacker;
  attack[attacker]=target;
  Action shield=attack;shield[actor]=target+3;
  auto no=resolve(State{hp},attack);
  auto yes=resolve(State{hp},shield);
  return no.after[target]==0&&yes.after[target]==1 &&
         no.after[actor]==4&&yes.after[actor]==3 &&
         yes.effective_aid_matrix[actor][target]==1;
}

// This is deliberately an invariance demonstration, not a moral-score condition.
// The same observation cannot encode two unobserved possible future attack plans.
inline bool unobserved_attack_plan_invariance(const FrozenState& s) {
  const auto& b=s.brains[0];
  HP hp{4,1,8};
  const auto p=b.forward(hp,0.).p;
  const auto q=b.forward(hp,0.).p;
  return p==q;
}

inline std::vector<Case> run_assay(const FrozenState &s) {
  std::vector<Case> rows;
  for(int actor=0;actor<3;++actor) for(int target=0;target<3;++target) {
    if(actor==target) continue;
    const int attacker=3-actor-target;
    for(int self_hp:{4,8}) for(int target_hp:{1,8}) for(int memory_mode:{0,1,2}) {
      Brain b=s.brains[actor]; // The only copy: frozen offline probe, never a new learning lineage.
      for(int i=0;i<3;++i){b.helped_recent[i]=0.;b.harmed_recent[i]=0.;b.helped_other_recent[i]=0.;}
      if(memory_mode==1)b.helped_recent[target]=8.;
      if(memory_mode==2)b.harmed_recent[target]=8.;
      HP hp{8,8,8};hp[actor]=self_hp;hp[target]=target_hp;hp[attacker]=8;
      const auto t=b.forward(hp,0.2);
      double sum=0.0;for(double p:t.p)sum+=p;
      if(!(std::abs(sum-1.)<1e-10) || t.p[target+3]<0||!std::isfinite(t.p[target+3]))
        throw std::runtime_error("invalid neural decision probabilities");
      if(!costly_protection_saves_a_life(actor,target,attacker))
        throw std::runtime_error("shield action is not genuinely costly and effective");
      Case row{};
      row.actor=actor;row.target=target;row.attacker=attacker;row.self_hp=self_hp;
      row.target_hp=target_hp;row.memory_mode=memory_mode;
      row.p_protect=t.p[target+3];row.probabilities=t.p;row.hidden=t.hidden;
      rows.push_back(row);
    }
  }
  return rows;
}
} // namespace prosocial
