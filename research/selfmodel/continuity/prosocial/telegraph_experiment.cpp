// Separate C++17 research lane. Synthetic telegraph is visible BEFORE shield decision.
// Uses the original triad::resolve for actual costs and rescue outcomes.
// Does NOT modify or claim learning in the 109M/200M frozen brains.
#include "triad.hpp"
#include <array>
#include <cmath>
#include <cstdint>
#include <iomanip>
#include <iostream>
#include <stdexcept>

namespace telegraph {
using triad::Action;
using triad::HP;
using triad::State;
using triad::FastRng;

struct Predecision {
  int helper_hp;
  int target_hp;
  bool warning;
};
struct Scenario {
  Predecision pre;
  bool attack_target; // Hidden until after decision, NEVER passed to inference.
};
struct Outcome {
  bool rescue;
  bool shield;
  bool unnecessary;
  int helper_hp_spent;
};
struct Metrics {
  int n=0, shield=0, rescues=0, missed=0, shams=0, nonlethal=0, helper_hp_spent=0;
  double utility=0;
};

inline Scenario generate(FastRng& rng, double reliability=0.85, double attack_prior=0.5) {
  if(!(reliability>=0.5 && reliability<=1.0 && attack_prior>=0.0 && attack_prior<=1.0))
    throw std::invalid_argument("invalid scenario parameters");
  // Intent is committed first, warning follows; shield choice is made later.
  const bool intent = rng.uniform() < attack_prior;
  const bool accurate = rng.uniform() < reliability;
  const bool warning = accurate ? intent : !intent;
  const int target_hp = rng.bound(2)==0 ? 1 : 8;
  return {{3,target_hp,warning},intent};
}

inline std::array<double,4> features(const Predecision& s, bool observe_warning) {
  const double critical=s.target_hp==1 ? 1.0 : 0.0;
  const double cue=observe_warning && s.warning ? 1.0 : 0.0;
  return {1.0,critical,cue,critical*cue};
}

inline double sigmoid(double x){return x<0 ? std::exp(x)/(1.0+std::exp(x)) : 1.0/(1.0+std::exp(-x));}

struct Head {
  std::array<double,4> weights{};
  bool observe_warning;
  explicit Head(bool observe=true):observe_warning(observe){}
  double risk(const Predecision& s)const {
    const auto x=features(s,observe_warning);
    double z=0;for(int j=0;j<4;j++)z+=weights[j]*x[j];
    return sigmoid(z);
  }
  bool shield(const Predecision& s)const {
    // Normative value of one avoided death = 4 helper HP, explicitly external.
    return s.helper_hp>1 && 4.0*risk(s)>1.0;
  }
  void train(const Predecision& pre, bool would_die, double eta=0.06) {
    const auto x=features(pre,observe_warning);
    const double grad=risk(pre)-(would_die ? 1.0:0.0);
    for(int j=0;j<4;j++)weights[j]-=eta*grad*x[j];
  }
};

inline Outcome resolve(const Scenario& s, bool shield) {
  const HP hp{s.pre.helper_hp,s.pre.target_hp,3};
  const int attacker_action = s.attack_target ? 1 : 2;
  const Action unshielded{2,2,attacker_action};
  const Action protected_move{4,2,attacker_action};
  const auto baseline=triad::resolve(State{hp},unshielded);
  const auto shielded=triad::resolve(State{hp},protected_move);
  if(shielded.after[0]!=hp[0]-1 || baseline.after[0]!=hp[0])
    throw std::runtime_error("helper cost did not match original rules");
  if(shielded.after[1]<baseline.after[1] || shielded.after[1]>baseline.after[1]+1)
    throw std::runtime_error("invalid rescue outcome");
  const bool potential=baseline.after[1]==0 && shielded.after[1]>0;
  const bool unnecessary=s.attack_target==false;
  return {potential && shield,shield,shield && unnecessary,shield ? 1 : 0};
}

inline void aggregate(Metrics& m, const Scenario& s, bool shield) {
  const Outcome result=resolve(s,shield);
  const bool rescue_possible = s.attack_target && s.pre.target_hp==1;
  ++m.n;
  m.shield+=result.shield;
  m.rescues+=result.rescue;
  m.missed+=(rescue_possible && !result.rescue);
  m.shams+=result.unnecessary;
  m.nonlethal+=(shield && s.attack_target && s.pre.target_hp!=1);
  m.helper_hp_spent+=result.helper_hp_spent;
  m.utility+=4.0*result.rescue-result.helper_hp_spent;
}

inline void train(Head& model, uint64_t seed, int n=40000) {
  FastRng rng(seed);
  for(int i=0;i<n;i++){
    const Scenario s=generate(rng);
    // The label comes from the outcome AFTER actions resolve, not from model inputs.
    const bool would_die=resolve(s,true).rescue;
    model.train(s.pre,would_die);
  }
}

struct Comparison {Metrics learned, blind, always, scrambled;};
inline Comparison evaluate(const Head& learned,const Head& blind,uint64_t seed,
                           int n=20000,double reliability=0.85,double prior=0.5){
  FastRng rng(seed);
  FastRng scramble(seed^0x4c2d9a91a523dd55ULL);
  Comparison r;
  for(int i=0;i<n;i++){
    Scenario s=generate(rng,reliability,prior);
    aggregate(r.learned,s,learned.shield(s.pre));
    aggregate(r.blind,s,blind.shield(s.pre));
    aggregate(r.always,s,s.pre.target_hp==1 && s.pre.helper_hp>1);
    // Negative control: warning independent of committed attacker intent.
    Predecision destroyed=s.pre;
    destroyed.warning=scramble.uniform()<0.5;
    aggregate(r.scrambled,s,learned.shield(destroyed));
  }
  return r;
}

inline void print_metrics(const char* label,const Metrics& m){
  std::cout<<"\""<<label<<"\":{\"cases\":"<<m.n
      <<",\"shields\":"<<m.shield<<",\"rescues\":"<<m.rescues
      <<",\"missed\":"<<m.missed<<",\"shams\":"<<m.shams
      <<",\"nonlethal_shields\":"<<m.nonlethal
      <<",\"helper_hp_spent\":"<<m.helper_hp_spent
      <<",\"utility\":"<<m.utility<<"}";
}
} // namespace telegraph

#ifndef ARE_TELEGRAPH_LIB_ONLY
int main(){
  using namespace telegraph;
  Head learned(true),blind(false);
  train(learned,101,40000);
  train(blind,101,40000);
  auto regular=evaluate(learned,blind,20261026,20000);
  auto shift=evaluate(learned,blind,20261027,20000,0.65,0.2);
  // Fail closed: the established setting must beat an uninformed shield rule.
  if(regular.learned.utility<=regular.always.utility ||
     regular.learned.utility<=regular.scrambled.utility ||
     regular.learned.rescues<=0 ||
     regular.learned.shams>=regular.always.shams)
    throw std::runtime_error("research control gate failed");
  std::cout<<std::fixed<<std::setprecision(7);
  std::cout<<"{\"schema\":\"are-telegraph-rescue-research-v1\","
           "\"evidence\":\"SEPARATE_NEW_CXX_POLICY_SYNTHETIC_WARNING_NOT_ORIGINAL_BRAIN\","
           "\"training_scenarios\":40000,\"heldout_seed\":20261026,"
           "\"original_brains_unchanged\":true,\"normative_life_value_hp\":4,"
           "\"weights\":[";
  for(int j=0;j<4;j++){if(j)std::cout<<',';std::cout<<learned.weights[j];}
  std::cout<<"],\"matched\":{";
  print_metrics("learned",regular.learned);std::cout<<',';
  print_metrics("blind",regular.blind);std::cout<<',';
  print_metrics("always",regular.always);std::cout<<',';
  print_metrics("scrambled",regular.scrambled);
  std::cout<<"},\"distribution_shift\":{";
  print_metrics("learned",shift.learned);std::cout<<',';
  print_metrics("always",shift.always);
  std::cout<<"}}\n";
}
#endif // ARE_TELEGRAPH_LIB_ONLY
