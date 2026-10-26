#pragma once
#include "triad.hpp"
#include <filesystem>
#include <iterator>
#include <type_traits>
#include <utility>
#include <cstddef>
#include <iomanip>

namespace triad {
namespace detail {
struct Buffer {
  std::vector<uint8_t> bytes;
  size_t position=0;
  template<class T> void put(const T& x){
    static_assert(std::is_trivially_copyable<T>::value,"checkpoint scalar must be POD");
    const auto *p=reinterpret_cast<const uint8_t*>(&x);bytes.insert(bytes.end(),p,p+sizeof(x));
  }
  template<class T> T get(){
    static_assert(std::is_trivially_copyable<T>::value,"checkpoint scalar must be POD");
    if(position>bytes.size()||sizeof(T)>bytes.size()-position)throw std::runtime_error("truncated checkpoint");
    T value{};std::memcpy(&value,bytes.data()+position,sizeof(T));position+=sizeof(T);return value;
  }
  void put_str(const std::string& s){if(s.size()>256)throw std::runtime_error("checkpoint string too long");put<uint32_t>(static_cast<uint32_t>(s.size()));bytes.insert(bytes.end(),s.begin(),s.end());}
  std::string get_str(){auto n=get<uint32_t>();if(n>256||position>bytes.size()||n>bytes.size()-position)throw std::runtime_error("invalid checkpoint string");std::string s(reinterpret_cast<const char*>(bytes.data()+position),n);position+=n;return s;}
  template<class T,size_t N>void put_arr(const std::array<T,N>& a){for(auto x:a)put(x);}
  template<class T,size_t N>void get_arr(std::array<T,N>& a){for(auto &x:a)x=get<T>();}
};
inline void pack_brain(Buffer& b,const Brain& x){
  b.put<int32_t>(x.identity);
  b.put<uint8_t>(x.learning);b.put<uint8_t>(x.remember);b.put<uint8_t>(x.damage);b.put<uint8_t>(x.dynamic_memory);
  for(int j=0;j<H;j++)for(int i=0;i<F;i++)b.put(x.w1[j][i]);
  for(int a=0;a<A;a++)for(int j=0;j<H;j++)b.put(x.w2[a][j]);
  for(double v:x.b1)b.put(v);for(double v:x.b2)b.put(v);
  for(int j=0;j<H;j++)for(int i=0;i<F;i++)b.put<uint8_t>(x.m1[j][i]);
  for(int a=0;a<A;a++)for(int j=0;j<H;j++)b.put<uint8_t>(x.m2[a][j]);
  for(uint64_t v:x.helped_by)b.put(v);for(uint64_t v:x.harmed_by)b.put(v);for(uint64_t v:x.helped_other)b.put(v);
  for(double v:x.helped_recent)b.put(v);for(double v:x.harmed_recent)b.put(v);for(double v:x.helped_other_recent)b.put(v);
  b.put(x.wins);b.put(x.losses);b.put(x.draws);b.put(x.updates);b.put(x.lesions);
  b.put(x.lesion_rng.state);
}
inline void unpack_brain(Buffer& b,Brain& x){
  if(b.get<int32_t>()!=x.identity || b.get<uint8_t>()!=x.learning || b.get<uint8_t>()!=x.remember || b.get<uint8_t>()!=x.damage || b.get<uint8_t>()!=x.dynamic_memory)
    throw std::runtime_error("checkpoint agent policy mismatch");
  for(int j=0;j<H;j++)for(int i=0;i<F;i++)x.w1[j][i]=b.get<double>();
  for(int a=0;a<A;a++)for(int j=0;j<H;j++)x.w2[a][j]=b.get<double>();
  for(double& v:x.b1)v=b.get<double>();for(double& v:x.b2)v=b.get<double>();
  int disabled=0;
  for(int j=0;j<H;j++)for(int i=0;i<F;i++){uint8_t f=b.get<uint8_t>();if(f>1)throw std::runtime_error("invalid lesion mask");x.m1[j][i]=f;if(!f){disabled++;if(x.w1[j][i]!=0)throw std::runtime_error("disabled connection not zeroed");}}
  for(int a=0;a<A;a++)for(int j=0;j<H;j++){uint8_t f=b.get<uint8_t>();if(f>1)throw std::runtime_error("invalid lesion mask");x.m2[a][j]=f;if(!f){disabled++;if(x.w2[a][j]!=0)throw std::runtime_error("disabled connection not zeroed");}}
  for(uint64_t &v:x.helped_by)v=b.get<uint64_t>();for(uint64_t &v:x.harmed_by)v=b.get<uint64_t>();for(uint64_t &v:x.helped_other)v=b.get<uint64_t>();
  for(double &v:x.helped_recent)v=b.get<double>();for(double &v:x.harmed_recent)v=b.get<double>();for(double &v:x.helped_other_recent)v=b.get<double>();
  x.wins=b.get<uint64_t>();x.losses=b.get<uint64_t>();x.draws=b.get<uint64_t>();x.updates=b.get<uint64_t>();x.lesions=b.get<uint64_t>();
  x.lesion_rng.state=b.get<uint64_t>();
  if(x.lesions!=static_cast<uint64_t>(disabled))throw std::runtime_error("lesion count and mask mismatch");
  if(!x.traces.empty())throw std::runtime_error("mid-episode checkpoint not supported");
}
inline void pack_summary(Buffer& b,const Summary& s){
  b.put(s.episodes);b.put(s.rounds);b.put(s.total_actions);b.put(s.draws);b.put(s.cap_hits);
  b.put_arr(s.wins);b.put_arr(s.effective_aids);b.put_arr(s.attacks_on_small);b.put_arr(s.self_attacks);
  for(const auto&a:s.effective_aid_matrix)b.put_arr(a);
  for(const auto&a:s.attack_matrix)b.put_arr(a);
}
inline void unpack_summary(Buffer& b,Summary& s){
  s.episodes=b.get<uint64_t>();s.rounds=b.get<uint64_t>();s.total_actions=b.get<uint64_t>();s.draws=b.get<uint64_t>();s.cap_hits=b.get<uint64_t>();
  b.get_arr(s.wins);b.get_arr(s.effective_aids);b.get_arr(s.attacks_on_small);b.get_arr(s.self_attacks);
  for(auto&a:s.effective_aid_matrix)b.get_arr(a);
  for(auto&a:s.attack_matrix)b.get_arr(a);
  if(s.episodes!=s.draws+s.wins[0]+s.wins[1]+s.wins[2])throw std::runtime_error("checkpoint win counters mismatch");
}
inline std::string sha_of(const Buffer& b){return hexsha(b.bytes.data(),b.bytes.size());}
inline void write_checkpoint(const std::string& path,uint64_t seed,const Summary& s,const std::array<Brain,3>& brains,const std::array<FastRng,3>& rngs,const SHA256_CTX& hasher){
  static_assert(std::is_trivially_copyable<SHA256_CTX>::value,"OpenSSL hash state cannot be serialized");
  Buffer b;
  b.put_str("ARE-SM-CONTINUITY-1");
  b.put<uint64_t>(OPENSSL_VERSION_NUMBER);b.put<uint32_t>(static_cast<uint32_t>(sizeof(SHA256_CTX)));
  b.put<uint32_t>(static_cast<uint32_t>(sizeof(double)));
  b.put(seed);b.put_str(s.arm);b.put<int32_t>(s.max_rounds);b.put<int32_t>(s.damage_interval);
  pack_summary(b,s);
  for(const auto&x:brains)pack_brain(b,x);
  for(const auto&r:rngs)b.put(r.state);
  b.put(hasher);
  const std::string hash=sha_of(b);
  for(char c:hash)b.put(c);
  namespace fs=std::filesystem;
  fs::path file(path),temp=file;
  temp+=".tmp";
  {std::ofstream out(temp,std::ios::binary|std::ios::trunc);if(!out)throw std::runtime_error("cannot create checkpoint");out.write(reinterpret_cast<const char*>(b.bytes.data()),static_cast<std::streamsize>(b.bytes.size()));out.flush();if(!out)throw std::runtime_error("cannot write complete checkpoint");}
  fs::rename(temp,file);
}
inline void read_checkpoint(const std::string& path,uint64_t seed,Summary& s,std::array<Brain,3>& brains,std::array<FastRng,3>& rngs,SHA256_CTX& hasher){
  std::ifstream in(path,std::ios::binary|std::ios::ate);if(!in)throw std::runtime_error("checkpoint not found");
  auto sz=in.tellg();if(sz<100||sz>65536)throw std::runtime_error("checkpoint size invalid");
  Buffer b;b.bytes.resize(static_cast<size_t>(sz));in.seekg(0);in.read(reinterpret_cast<char*>(b.bytes.data()),sz);if(!in)throw std::runtime_error("cannot read checkpoint");
  if(b.bytes.size()<64)throw std::runtime_error("corrupt checkpoint");
  const std::string expected(reinterpret_cast<const char*>(b.bytes.data()+b.bytes.size()-64),64);
  b.bytes.resize(b.bytes.size()-64);
  if(sha_of(b)!=expected)throw std::runtime_error("checkpoint sha256 mismatch");
  if(b.get_str()!="ARE-SM-CONTINUITY-1")throw std::runtime_error("checkpoint version mismatch");
  if(b.get<uint64_t>()!=OPENSSL_VERSION_NUMBER || b.get<uint32_t>()!=sizeof(SHA256_CTX)||b.get<uint32_t>()!=sizeof(double))throw std::runtime_error("checkpoint runtime ABI mismatch");
  if(b.get<uint64_t>()!=seed || b.get_str()!=s.arm || b.get<int32_t>()!=s.max_rounds || b.get<int32_t>()!=s.damage_interval)throw std::runtime_error("checkpoint simulation config mismatch");
  unpack_summary(b,s);
  for(auto&x:brains)unpack_brain(b,x);
  for(auto&r:rngs)r.state=b.get<uint64_t>();
  hasher=b.get<SHA256_CTX>();
  if(b.position!=b.bytes.size())throw std::runtime_error("checkpoint trailing data");
  for(int i=0;i<3;i++)if(brains[i].wins!=s.wins[i] || brains[i].draws!=s.draws || brains[i].wins+brains[i].losses+brains[i].draws!=s.episodes)throw std::runtime_error("checkpoint personal counters mismatch");
}
inline void write_arr(std::ostream&os,const double *arr,int n){os<<'[';for(int i=0;i<n;i++){if(i)os<<',';os<<arr[i];}os<<']';}
inline void observe_pre_decision(std::ostream& out,uint64_t ep,int tick,const HP& hp,const std::array<Brain,3>& brains,const Action& moves,const std::array<uint64_t,3>& policy_rng_before){
  // Out-of-band probe: reads already computed Trace; makes NO calls to forward(), choose(), RNG or update().
  for(int i=0;i<3;i++){
    if(moves[i]<0)continue;
    const Brain& b=brains[i];const Trace& t=b.traces.back();
    out<<std::setprecision(17)<<"{\"schema\":\"are-selfmodel-observer-1\",\"phase\":\"pre_decision\",\"episode\":"<<ep
       <<",\"tick\":"<<tick<<",\"agent\":"<<i<<",\"hp\":["<<hp[0]<<','<<hp[1]<<','<<hp[2]<<']'
       <<",\"action\":"<<moves[i]<<",\"policy_rng_before\":"<<policy_rng_before[i]<<",\"short_term_trace_count\":"<<b.traces.size()<<",\"input\":";
    write_arr(out,t.x.data(),F);out<<",\"hidden\":";write_arr(out,t.hidden.data(),H);out<<",\"probabilities\":";write_arr(out,t.p.data(),A);
    out<<",\"memory\":{\"helped_by\":["<<b.helped_by[0]<<','<<b.helped_by[1]<<','<<b.helped_by[2]<<']'
       <<",\"harmed_by\":["<<b.harmed_by[0]<<','<<b.harmed_by[1]<<','<<b.harmed_by[2]<<']'
       <<",\"helped_other\":["<<b.helped_other[0]<<','<<b.helped_other[1]<<','<<b.helped_other[2]<<"]}"
       <<",\"helped_recent\":";write_arr(out,b.helped_recent,3);
    out<<",\"harmed_recent\":";write_arr(out,b.harmed_recent,3);
    out<<",\"weights_sha256\":\""<<b.weight_sha()<<"\",\"mask_sha256\":\""<<b.mask_sha()<<"\"}"
       <<'\n';
  }
  out.flush();if(!out)throw std::runtime_error("observer write failed");
}
inline void observe_episode_end(std::ostream& out,uint64_t ep,int winner,const std::array<Brain,3>& brains){
  out<<"{\"schema\":\"are-selfmodel-observer-1\",\"phase\":\"post_update\",\"episode\":"<<ep<<",\"winner\":"<<winner<<",\"agents\":[";
  for(int i=0;i<3;i++){if(i)out<<',';auto &b=brains[i];out<<"{\"id\":"<<i<<",\"active\":"<<b.active()<<",\"lesions\":"<<b.lesions
    <<",\"wins\":"<<b.wins<<",\"losses\":"<<b.losses<<",\"helped_recent\":";write_arr(out,b.helped_recent,3);
    out<<",\"harmed_recent\":";write_arr(out,b.harmed_recent,3);
    out<<",\"weights_sha256\":\""<<b.weight_sha()<<"\",\"mask_sha256\":\""<<b.mask_sha()<<"\"}";}
  out<<"]}\n";out.flush();if(!out)throw std::runtime_error("observer post-update write failed");
}
} // namespace detail

inline Summary simulate_continuous(uint64_t seed,const std::string& arm,uint64_t target_episodes,int max_rounds,int damage_interval,uint64_t checkpoint_every,const std::string& checkpoint_path,const std::string& observer_path,uint64_t observer_every,const std::string& resume_path){
  bool learn=true,remember=true,damage=true;
  if(arm=="adaptive_damage"){}else if(arm=="adaptive_intact")damage=false;
  else if(arm=="adaptive_amnesia")remember=false;
  else if(arm=="frozen_damage")learn=false;
  else throw std::invalid_argument("unknown arm");
  if(target_episodes<1||target_episodes>200000000ULL||max_rounds<1||max_rounds>120||damage_interval<1||damage_interval>100000000||checkpoint_every<1||observer_every>100000000ULL)throw std::invalid_argument("invalid bounded settings");
  if(!observer_path.empty()&&observer_every==0)throw std::invalid_argument("observer_every must be positive for observer path");
  if(!observer_path.empty() && (!checkpoint_path.empty()&&observer_path==checkpoint_path || !resume_path.empty()&&observer_path==resume_path))throw std::invalid_argument("observer and checkpoint paths collide");
  std::array<Brain,3> brains={Brain(0,seed,learn,remember,damage,max_rounds),Brain(1,seed,learn,remember,damage,max_rounds),Brain(2,seed,learn,remember,damage,max_rounds)};
  std::array<FastRng,3> rngs={FastRng(seedmix(seed,0,3)),FastRng(seedmix(seed,1,3)),FastRng(seedmix(seed,2,3))};
  for(auto& b:brains)b.dynamic_memory=true;
  SHA256_CTX hasher{};SHA256_Init(&hasher);
  Summary s;s.seed=seed;s.arm=arm;s.max_rounds=max_rounds;s.damage_interval=damage_interval;s.dynamic_memory_enabled=true;
  if(!resume_path.empty())detail::read_checkpoint(resume_path,seed,s,brains,rngs,hasher);
  if(target_episodes<s.episodes)throw std::runtime_error("target episodes smaller than checkpoint episode");
  std::ofstream observer;
  if(!observer_path.empty()){
    observer.open(observer_path,std::ios::out|std::ios::app);
    if(!observer)throw std::runtime_error("cannot open observer output");
  }
  auto start=std::chrono::steady_clock::now();
  for(uint64_t ep=s.episodes;ep<target_episodes;ep++){
    HP hp=INITIAL_HP;int tick=0;bool near_end_sampled=false;
    for(;tick<max_rounds;tick++){
      int alive=0;for(int h:hp)alive+=h>0;if(alive<=1)break;
      Action moves{-1,-1,-1};std::array<uint64_t,3> rng_before{};
      bool sample_episode=observer.is_open() && ep%observer_every==0;
      bool near_end=sample_episode && !near_end_sampled && tick>0 && (hp[0]<=2 || hp[1]<=2 || hp[2]<=2);
      bool monitor=sample_episode && (tick==0 || tick==max_rounds/2 || near_end);
      if(near_end)near_end_sampled=true;
      for(int i=0;i<3;i++)if(hp[i]>0){if(monitor)rng_before[i]=rngs[i].state;moves[i]=brains[i].choose(hp,static_cast<double>(tick)/max_rounds,rngs[i]);}
      if(monitor)detail::observe_pre_decision(observer,ep,tick,hp,brains,moves,rng_before);
      Events e=resolve(State{hp},moves);chain_event(hasher,ep,tick,hp,moves,e.after);
      for(int i=0;i<3;i++)if(moves[i]>=0){
        s.total_actions++;if(moves[i]<3){int t=moves[i]%3;s.attack_matrix[i][t]++;if(t==2&&i!=2)s.attacks_on_small[i]++;if(t==i)s.self_attacks[i]++;for(auto&b:brains)b.on_attack(i,t);}
      }
      for(int i=0;i<3;i++)for(int t=0;t<3;t++)if(e.effective_aid_matrix[i][t]){s.effective_aids[i]++;s.effective_aid_matrix[i][t]++;for(auto&b:brains)b.on_help(i,t);}
      hp=e.after;s.rounds++;
    }
    int survivor=-1,count=0;for(int i=0;i<3;i++)if(hp[i]>0){survivor=i;count++;}
    int winner=count==1?survivor:-1;
    if(winner<0)s.draws++;else s.wins[winner]++;
    if(tick==max_rounds&&count>1)s.cap_hits++;
    for(auto&b:brains)b.on_result(winner,damage_interval);
    s.episodes=ep+1;
    if(observer.is_open()&&ep%observer_every==0)detail::observe_episode_end(observer,ep,winner,brains);
    if(!checkpoint_path.empty()&&(s.episodes%checkpoint_every==0||s.episodes==target_episodes)){
      detail::write_checkpoint(checkpoint_path,seed,s,brains,rngs,hasher);
    }
  }
  auto stop=std::chrono::steady_clock::now();s.elapsed_seconds=std::chrono::duration<double>(stop-start).count();
  SHA256_CTX copy=hasher;unsigned char digest[SHA256_DIGEST_LENGTH];SHA256_Final(digest,&copy);
  // Original algorithm hex-encodes the final digest rather than hashing it again.
  constexpr char alphabet[]="0123456789abcdef";std::string hash;hash.reserve(64);
  for(unsigned char c:digest){hash+=alphabet[c>>4];hash+=alphabet[c&15];}s.event_rolling_sha256=hash;
  for(int i=0;i<3;i++)s.agents[i]=snapshot(brains[i]);
  return s;
}
} // namespace triad
