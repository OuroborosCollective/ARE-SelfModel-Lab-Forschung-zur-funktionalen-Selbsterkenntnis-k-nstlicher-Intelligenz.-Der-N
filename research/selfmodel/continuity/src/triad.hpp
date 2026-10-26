#pragma once
#include <array>
#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <fstream>
#include <iomanip>
#include <limits>
#include <random>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>
#include <openssl/sha.h>

namespace triad {
constexpr int F=15, H=12, A=6, C=252;
using HP=std::array<int,3>;
using Action=std::array<int,3>;
constexpr HP INITIAL_HP={16,16,9};
constexpr const char* names[3]={"Gross_A","Gross_B","Klein"};
struct State { HP hp; };
struct Events {
  HP after{}; std::array<std::array<int,3>,3> attacks{};
  std::array<std::array<int,3>,3> aids{};
  HP effective_aids{}; std::array<std::array<int,3>,3> effective_aid_matrix{};
  HP damage{};
};
inline Events resolve(const State& state, const Action& moves){
  Events e; HP costs{}; std::array<int,3> already{}; e.after=state.hp;
  for(int i=0;i<3;i++){
    if(state.hp[i]==0){if(moves[i]!=-1)throw std::runtime_error("dead actor acted");continue;}
    int m=moves[i], t=m%3;
    if(m<0||m>=6||state.hp[t]==0)throw std::runtime_error("illegal move");
    if(m<3){e.attacks[i][t]++;e.damage[t]++;}
    else{if(t==i||state.hp[i]<=1)throw std::runtime_error("illegal shield"); e.aids[i][t]++;costs[i]++;}
  }
  // Shield resolution is deterministic and mirrors Python actor order.
  for(int i=0;i<3;i++)for(int j=0;j<3;j++)if(e.aids[i][j]){
    if(already[j]<e.damage[j]){already[j]++;e.effective_aids[i]++;e.effective_aid_matrix[i][j]++;}
  }
  for(int k=0;k<3;k++)e.after[k]=std::max(0,state.hp[k]-e.damage[k]+already[k]-costs[k]);
  return e;
}
struct FastRng {
  uint64_t state;
  explicit FastRng(uint64_t seed):state(seed){}
  uint64_t u64(){uint64_t z=(state+=0x9e3779b97f4a7c15ULL);z=(z^(z>>30))*0xbf58476d1ce4e5b9ULL;z=(z^(z>>27))*0x94d049bb133111ebULL;return z^(z>>31);}
  double uniform(){return static_cast<double>(u64()>>11)*0x1.0p-53;}
  int bound(int n){return static_cast<int>(u64()%static_cast<uint64_t>(n));}
};
inline uint64_t seedmix(uint64_t seed,int id,int stream){
  FastRng r(seed ^ (static_cast<uint64_t>(id+7)*0x9e3779b97f4a7c15ULL) ^ (static_cast<uint64_t>(stream+17)*0xbf58476d1ce4e5b9ULL));return r.u64();
}
inline std::string hexsha(const void* data,size_t n){unsigned char b[SHA256_DIGEST_LENGTH];SHA256(reinterpret_cast<const unsigned char*>(data),n,b);constexpr char hex[]="0123456789abcdef";std::string out;out.reserve(64);for(unsigned char v:b){out+=hex[v>>4];out+=hex[v&15];}return out;}
struct Trace {std::array<double,F> x{}; std::array<double,H> hidden{};std::array<double,A> p{};int action=0;};
struct Brain {
  int identity;
  bool learning,remember,damage;
  double w1[H][F]{},w2[A][H]{},b1[H]{},b2[A]{};
  bool m1[H][F]{},m2[A][H]{};
  uint64_t helped_by[3]{},harmed_by[3]{},helped_other[3]{};
  // Optional in the continuity protocol: bounded recency-sensitive social memory.
  bool dynamic_memory=false;
  double helped_recent[3]{},harmed_recent[3]{},helped_other_recent[3]{};
  uint64_t wins=0, losses=0, draws=0, updates=0,lesions=0;
  FastRng lesion_rng;
  std::vector<Trace> traces;
  Brain(int id,uint64_t seed,bool learn,bool mem,bool dmg,int max_rounds):identity(id),learning(learn),remember(mem),damage(dmg),lesion_rng(seedmix(seed,id,2)){
    FastRng init(seedmix(seed,id,1));
    for(int j=0;j<H;j++)for(int i=0;i<F;i++){w1[j][i]=init.uniform()*0.54-0.27;m1[j][i]=true;}
    for(int a=0;a<A;a++)for(int j=0;j<H;j++){w2[a][j]=init.uniform()*0.54-0.27;m2[a][j]=true;}
    traces.reserve(max_rounds);
  }
  int active() const {return C-static_cast<int>(lesions);}
  std::array<double,F> observe(const HP &hp,double fraction) const {
    std::array<double,F> x{};
    for(int i=0;i<3;i++){
      x[i]=static_cast<double>(std::max(0,hp[i]))/INITIAL_HP[i];
      if(remember){
        if(dynamic_memory){x[3+i]=helped_recent[i]/(8.+helped_recent[i]);x[6+i]=harmed_recent[i]/(8.+harmed_recent[i]);x[9+i]=helped_other_recent[i]/(8.+helped_other_recent[i]);}
        else{x[3+i]=std::min(1.,helped_by[i]/8.);x[6+i]=std::min(1.,harmed_by[i]/8.);x[9+i]=std::min(1.,helped_other[i]/8.);}
      }
    }
    x[12]=active()/static_cast<double>(C);x[13]=fraction;x[14]=1.;return x;
  }
  Trace forward(const HP& hp,double fraction)const {
    Trace t; t.x=observe(hp,fraction);
    for(int j=0;j<H;j++){double v=b1[j];for(int i=0;i<F;i++)v+=w1[j][i]*t.x[i];t.hidden[j]=std::tanh(v);}
    double scores[A];double mx=-1e100;
    for(int a=0;a<A;a++){
      int target=a%3;
      bool legal=hp[target]>0 && (a<3 || (target!=identity && hp[identity]>1));
      if(legal){double s=b2[a];for(int j=0;j<H;j++)s+=w2[a][j]*t.hidden[j];scores[a]=s;mx=std::max(mx,s);}
      else scores[a]=-1e100;
    }
    double sum=0.;for(int a=0;a<A;a++)if(scores[a]>-1e99){t.p[a]=std::exp(scores[a]-mx);sum+=t.p[a];}
    for(int a=0;a<A;a++)t.p[a]/=sum;
    return t;
  }
  int choose(const HP& hp,double fraction,FastRng& rng){
    Trace t=forward(hp,fraction);
    double x=rng.uniform(), cumulative=0.0;int chosen=-1;
    for(int a=0;a<A;a++){cumulative+=t.p[a];if(t.p[a]>0&&x<=cumulative){chosen=a;break;}}
    if(chosen<0){chosen=static_cast<int>(std::max_element(t.p.begin(),t.p.end())-t.p.begin());}
    t.action=chosen;traces.push_back(t);return chosen;
  }
  void on_attack(int actor,int target){if(remember&&target==identity&&actor!=identity){harmed_by[actor]++;if(dynamic_memory)harmed_recent[actor]+=1.;}}
  void on_help(int actor,int target){if(!remember)return;
    if(target==identity&&actor!=identity){helped_by[actor]++;if(dynamic_memory)helped_recent[actor]+=1.;}
    if(actor==identity&&target!=identity){helped_other[target]++;if(dynamic_memory)helped_other_recent[target]+=1.;}
  }
  void lesion(){if(lesions>=C)return;int available=C-static_cast<int>(lesions);int nth=lesion_rng.bound(available);int selected=-1;for(int i=0;i<C;i++){
      bool active_bit=i<H*F?m1[i/F][i%F]:m2[(i-H*F)/H][(i-H*F)%H];
      if(active_bit&&nth--==0){selected=i;break;}
    }
    if(selected<0)throw std::runtime_error("lesion index invariant");
    if(selected<H*F){int j=selected/F,i=selected%F;m1[j][i]=false;w1[j][i]=0;}
    else{int a=(selected-H*F)/H,j=(selected-H*F)%H;m2[a][j]=false;w2[a][j]=0;}
    lesions++;
  }
  void on_result(int winner,int interval){
    double reward=winner==identity?1.0:(winner<0?-0.25:-1.0);
    if(winner<0)draws++;else if(winner==identity)wins++;else losses++;
    if(learning&&!traces.empty()){
      const double lr=0.04/static_cast<double>(traces.size());
      for(const Trace& t:traces){
        double delta[A];for(int a=0;a<A;a++)delta[a]=((a==t.action?1.0:0.0)-t.p[a])*lr*reward;
        double gh[H];for(int j=0;j<H;j++){
          double value=0.;for(int a=0;a<A;a++)value+=delta[a]*w2[a][j];
          gh[j]=(1-t.hidden[j]*t.hidden[j])*value;
        }
        for(int a=0;a<A;a++){
          b2[a]+=delta[a];for(int j=0;j<H;j++)if(m2[a][j])w2[a][j]+=delta[a]*t.hidden[j];
        }
        for(int j=0;j<H;j++){
          b1[j]+=gh[j];for(int i=0;i<F;i++)if(m1[j][i])w1[j][i]+=gh[j]*t.x[i];
        }
      }
      updates++;
    }
    if(damage&&winner>=0&&winner!=identity && (losses==1 || (losses-1)%static_cast<uint64_t>(interval)==0))lesion();
    traces.clear();
    if(dynamic_memory){for(int i=0;i<3;i++){helped_recent[i]*=0.98;harmed_recent[i]*=0.98;helped_other_recent[i]*=0.98;}}
  }
  double helper_swap_l1()const{
    if(!remember)return 0.;Brain x=*this;Brain y=*this;
    for(int i=0;i<3;i++){x.helped_by[i]=0;y.helped_by[i]=0;}
    int i0=identity==0?1:0;int i1=identity==2?1:2;
    x.helped_by[i0]=8;y.helped_by[i1]=8;
    auto p=x.forward(INITIAL_HP,0).p,q=y.forward(INITIAL_HP,0).p;
    double sum=0;for(int a=0;a<A;a++)sum+=std::abs(p[a]-q[a]);return sum;
  }
  std::string weight_sha() const {
    std::array<double,C+H+A> arr{};size_t k=0;
    for(int j=0;j<H;j++)for(int i=0;i<F;i++)arr[k++]=w1[j][i];
    for(int a=0;a<A;a++)for(int j=0;j<H;j++)arr[k++]=w2[a][j];
    for(int j=0;j<H;j++)arr[k++]=b1[j];for(int a=0;a<A;a++)arr[k++]=b2[a];
    return hexsha(arr.data(),arr.size()*sizeof(double));
  }
  std::string mask_sha() const {
    std::array<unsigned char,C> arr{};int k=0;
    for(int j=0;j<H;j++)for(int i=0;i<F;i++)arr[k++]=m1[j][i];
    for(int a=0;a<A;a++)for(int j=0;j<H;j++)arr[k++]=m2[a][j];
    return hexsha(arr.data(),arr.size());
  }
};
struct AgentResult {
 uint64_t wins=0,losses=0,draws=0,updates=0,lesions=0;int active=252;
 std::array<uint64_t,3> helped_by{},harmed_by{},helped_other{};
 double helper_swap_L1=0;std::string weights_sha256,mask_sha256;
};
inline AgentResult snapshot(const Brain& b){
  AgentResult a;a.wins=b.wins;a.losses=b.losses;a.draws=b.draws;a.updates=b.updates;a.lesions=b.lesions;a.active=b.active();
  for(int i=0;i<3;i++){a.helped_by[i]=b.helped_by[i];a.harmed_by[i]=b.harmed_by[i];a.helped_other[i]=b.helped_other[i];}
  a.helper_swap_L1=b.helper_swap_l1();a.weights_sha256=b.weight_sha();a.mask_sha256=b.mask_sha();return a;
}
inline std::string enc_u64(const std::array<uint64_t,3> &v){return "["+std::to_string(v[0])+","+std::to_string(v[1])+","+std::to_string(v[2])+"]";}
struct Summary{
  uint64_t episodes=0,rounds=0,total_actions=0,draws=0,cap_hits=0;
  std::array<uint64_t,3> wins{},effective_aids{},attacks_on_small{},self_attacks{};
  std::array<std::array<uint64_t,3>,3> effective_aid_matrix{},attack_matrix{};
  AgentResult agents[3];std::string arm;uint64_t seed=0;int max_rounds=0,damage_interval=0;
  double elapsed_seconds=0;std::string event_rolling_sha256;bool dynamic_memory_enabled=false;
  std::string to_json()const{
    std::ostringstream out;out<<std::setprecision(14);
    out<<"{\"schema\":\"are-selfmodel-three-brains-cpp-v1\",\"arm\":\""<<arm<<"\",\"seed\":"<<seed
       <<",\"episodes_completed\":"<<episodes<<",\"rounds\":"<<rounds<<",\"total_actions\":"<<total_actions
       <<",\"wins\":"<<enc_u64(wins)<<",\"draws\":"<<draws
       <<",\"max_rounds\":"<<max_rounds<<",\"damage_interval\":"<<damage_interval
       <<",\"round_cap_hits\":"<<cap_hits<<",\"effective_aids\":"<<enc_u64(effective_aids)
       <<",\"attacks_on_small\":"<<enc_u64(attacks_on_small)<<",\"self_attacks\":"<<enc_u64(self_attacks)
       <<",\"attack_matrix\":[";
    for(int i=0;i<3;i++){if(i)out<<',';out<<enc_u64(attack_matrix[i]);}out<<"],\"effective_aid_matrix\":[";
    for(int i=0;i<3;i++){if(i)out<<',';out<<enc_u64(effective_aid_matrix[i]);}out<<"],\"agents\":[";
    for(int i=0;i<3;i++){
      if(i)out<<',';const auto&a=agents[i];
      out<<"{\"name\":\""<<names[i]<<"\",\"wins\":"<<a.wins<<",\"losses\":"<<a.losses
         <<",\"draws\":"<<a.draws<<",\"updates\":"<<a.updates<<",\"damage_events\":"<<a.lesions
         <<",\"active_connections\":"<<a.active<<",\"helped_by\":"<<enc_u64(a.helped_by)
         <<",\"harmed_by\":"<<enc_u64(a.harmed_by)<<",\"helped_other\":"<<enc_u64(a.helped_other)
         <<",\"helper_swap_L1\":"<<a.helper_swap_L1
         <<",\"weights_sha256\":\""<<a.weights_sha256<<"\",\"mask_sha256\":\""<<a.mask_sha256<<"\"}";
    }
    out<<"],\"elapsed_seconds\":"<<elapsed_seconds
       <<",\"rolling_event_sha256\":\""<<event_rolling_sha256<<"\""
       <<",\"evidence_level\":\"deterministic_nonlinguistic_cpp_neural_policies\",\"real_process_kills\":false"
       <<",\"subjective_experience_measured\":false,\"consciousness_inferred\":false,\"memory_features_clip_at_8\":"<<(dynamic_memory_enabled?"false":"true")
       <<",\"dynamic_recency_memory\":"<<(dynamic_memory_enabled?"true":"false")<<",\"language_model\":false}";
    return out.str();
  }
};
inline void chain_event(SHA256_CTX& ctx,uint64_t episode,int tick,const HP& before,const Action& choices,const HP& after){
  uint64_t vals[11]={episode,static_cast<uint64_t>(tick),static_cast<uint64_t>(before[0]),static_cast<uint64_t>(before[1]),static_cast<uint64_t>(before[2]),static_cast<uint64_t>(choices[0]+1),static_cast<uint64_t>(choices[1]+1),static_cast<uint64_t>(choices[2]+1),static_cast<uint64_t>(after[0]),static_cast<uint64_t>(after[1]),static_cast<uint64_t>(after[2])};
  SHA256_Update(&ctx,vals,sizeof(vals));
}
inline Summary simulate(uint64_t seed,const std::string& arm,uint64_t episodes,int max_rounds,int damage_interval,uint64_t checkpoint_every,const std::string &checkpoint_file=""){
  bool learn=true,remember=true,damage=true;
  if(arm=="adaptive_damage"){}else if(arm=="adaptive_intact")damage=false;
  else if(arm=="adaptive_amnesia")remember=false;
  else if(arm=="frozen_damage")learn=false;
  else throw std::invalid_argument("unknown arm");
  if(episodes<1||episodes>200000000ULL||max_rounds<1||max_rounds>120||damage_interval<1||damage_interval>100000000||checkpoint_every<1)throw std::invalid_argument("invalid bounded settings");
  std::array<Brain,3> brains={Brain(0,seed,learn,remember,damage,max_rounds),Brain(1,seed,learn,remember,damage,max_rounds),Brain(2,seed,learn,remember,damage,max_rounds)};
  std::array<FastRng,3> rngs={FastRng(seedmix(seed,0,3)),FastRng(seedmix(seed,1,3)),FastRng(seedmix(seed,2,3))};
  SHA256_CTX hasher;SHA256_Init(&hasher);
  std::ofstream checkpoint;
  if(!checkpoint_file.empty()){checkpoint.open(checkpoint_file,std::ios::out|std::ios::trunc);if(!checkpoint)throw std::runtime_error("cannot open checkpoint");}
  auto start=std::chrono::steady_clock::now();Summary s;s.seed=seed;s.arm=arm;s.max_rounds=max_rounds;s.damage_interval=damage_interval;
  for(uint64_t ep=0;ep<episodes;ep++){
    HP hp=INITIAL_HP;int tick=0;
    for(;tick<max_rounds;tick++){
      int alive=0;for(int v:hp)alive+=v>0;if(alive<=1)break;
      Action moves{-1,-1,-1};
      for(int i=0;i<3;i++)if(hp[i]>0)moves[i]=brains[i].choose(hp,static_cast<double>(tick)/max_rounds,rngs[i]);
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
    if(checkpoint.is_open()&&(s.episodes%checkpoint_every==0||s.episodes==episodes)){
      checkpoint<<"{\"episode\":"<<s.episodes<<",\"wins\":"<<enc_u64(s.wins)<<",\"draws\":"<<s.draws
               <<",\"active\":["<<brains[0].active()<<","<<brains[1].active()<<","<<brains[2].active()<<"],\"aids\":"<<enc_u64(s.effective_aids)<<"}\n";
      checkpoint.flush();
    }
  }
  auto stop=std::chrono::steady_clock::now();s.elapsed_seconds=std::chrono::duration<double>(stop-start).count();
  unsigned char hash[SHA256_DIGEST_LENGTH];SHA256_Final(hash,&hasher);char buf[65];constexpr char alphabet[]="0123456789abcdef";for(int i=0;i<32;i++){buf[i*2]=alphabet[hash[i]>>4];buf[i*2+1]=alphabet[hash[i]&15];}buf[64]=0;s.event_rolling_sha256=buf;
  for(int i=0;i<3;i++)s.agents[i]=snapshot(brains[i]);
  return s;
}
} // namespace triad
