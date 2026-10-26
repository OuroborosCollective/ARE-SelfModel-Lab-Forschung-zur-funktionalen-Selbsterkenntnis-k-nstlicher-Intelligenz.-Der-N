#pragma once
// Frozen one-way helping assay. An action counts as helping only if the
// original game rules show both irreversible donor cost and beneficiary life saved.
// Future attack intent is not part of the original network observation vector.
#include "social_probe.hpp"
#include <array>
#include <cmath>
#include <cstdint>
#include <stdexcept>
#include <string>
#include <vector>

namespace oneway {
using namespace triad;
using namespace prosocial;

struct Row {
  int actor=0, target=0, attacker=0, self_hp=0, target_hp=0, memory_mode=0;
  bool attacker_hits_target=false, prevented_death=false;
  int helper_cost=0, target_delta_on_shield=0;
  int after_shield_hp=0, after_attack_hp=0;
  double p_shield=0, p_sum=0;
  std::array<double,6> probabilities{};
  std::array<double,12> hidden{};
  std::string actor_weights_sha256, actor_mask_sha256;
};
struct Study {
  Summary summary;
  std::array<Brain,3> brains;
  std::vector<Row> rows;
  std::string checkpoint_sha256;
  bool brains_unchanged=false;
  const bool observability_warning_visible=false;
  explicit Study(FrozenState&& frozen)
    : summary(std::move(frozen.summary)), brains(std::move(frozen.brains)){}
};
inline std::array<std::string,3> identify(const std::array<Brain,3>& brains){
  return {brains[0].weight_sha()+brains[0].mask_sha(),
          brains[1].weight_sha()+brains[1].mask_sha(),
          brains[2].weight_sha()+brains[2].mask_sha()};
}
inline Row one_case(const Brain& original,int actor,int target,int self_hp,
                    int target_hp,int memory_mode,bool attacker_hits_target){
  if(actor<0||actor>2||target<0||target>2||actor==target ||
     (self_hp!=3 && self_hp!=8) || (target_hp!=1 && target_hp!=8) ||
     memory_mode<0||memory_mode>2)throw std::invalid_argument("invalid scenario");
  const int attacker=3-actor-target;
  Brain b=original; // Frozen copy of one exact experienced brain.
  if(b.identity!=actor)throw std::invalid_argument("actor checkpoint mismatch");
  for(int i=0;i<3;i++){
    b.helped_recent[i]=0.0;
    b.harmed_recent[i]=0.0;
    b.helped_other_recent[i]=0.0;
  }
  // In held-out situations the target's earlier behavior is independently set.
  if(memory_mode==1)b.helped_recent[target]=8.0;
  else if(memory_mode==2)b.harmed_recent[target]=8.0;
  HP hp{8,8,8}; hp[actor]=self_hp;hp[target]=target_hp;hp[attacker]=8;
  const auto trace=b.forward(hp,0.2);
  double p_sum=0.;for(double p:trace.p){if(!std::isfinite(p)||p<0||p>1)throw std::runtime_error("invalid policy probability");p_sum+=p;}
  if(std::abs(p_sum-1.)>1e-10)throw std::runtime_error("policy not normalized");
  Action baseline{-1,-1,-1};
  baseline[actor]=attacker; baseline[target]=attacker;
  // Threat vs sham occurs AFTER decision. It cannot leak into the neural input.
  baseline[attacker]=attacker_hits_target?target:actor;
  Action shield=baseline;shield[actor]=3+target;
  const auto no=resolve(State{hp},baseline);
  const auto yes=resolve(State{hp},shield);
  const int delta=yes.after[target]-no.after[target];
  const int donor_cost=no.after[actor]-yes.after[actor];
  if(donor_cost!=1 || delta!=(attacker_hits_target?1:0))
    throw std::runtime_error("rescue game physics violated");
  const bool saved=attacker_hits_target && target_hp==1 && no.after[target]==0 && yes.after[target]==1;
  Row row;
  row.actor=actor;row.target=target;row.attacker=attacker;row.self_hp=self_hp;
  row.target_hp=target_hp;row.memory_mode=memory_mode;row.attacker_hits_target=attacker_hits_target;
  row.prevented_death=saved;row.helper_cost=donor_cost;row.target_delta_on_shield=delta;
  row.after_shield_hp=yes.after[target];row.after_attack_hp=no.after[target];
  row.p_shield=trace.p[3+target];row.p_sum=p_sum;
  row.probabilities=trace.p;row.hidden=trace.hidden;
  row.actor_weights_sha256=original.weight_sha();row.actor_mask_sha256=original.mask_sha();
  return row;
}
inline Study evaluate(const std::string& checkpoint,uint64_t expected_episodes){
  if(expected_episodes!=109000000ULL && expected_episodes!=200000000ULL)
    throw std::invalid_argument("only two preregistered original checkpoints allowed");
  FrozenState initial=read_frozen_checkpoint(checkpoint);
  if(initial.summary.episodes!=expected_episodes)throw std::runtime_error("wrong brain checkpoint episode");
  Study study(std::move(initial));
  study.checkpoint_sha256=sha_of_file(checkpoint);
  const auto before=identify(study.brains);
  for(int actor=0;actor<3;actor++)for(int target=0;target<3;target++){
    if(actor==target)continue;
    for(int self_hp:{3,8})for(int target_hp:{1,8})for(int memory_mode:{0,1,2})
      for(int hits:{0,1}){
        study.rows.push_back(one_case(study.brains[actor],actor,target,self_hp,target_hp,memory_mode,hits==1));
      }
  }
  study.brains_unchanged=(before==identify(study.brains));
  if(study.rows.size()!=144 || !study.brains_unchanged)
    throw std::runtime_error("frozen assay invariant violated");
  return study;
}
inline bool paired_attack_invariance(const Study& study){
  // All state seen by the original 15-channel brain is identical between
  // future attack and sham; hence decision odds must be exactly equal.
  for(size_t i=0;i<study.rows.size();i+=2){
    const auto& a=study.rows[i];const auto& b=study.rows[i+1];
    if(a.attacker_hits_target||!b.attacker_hits_target||a.p_shield!=b.p_shield||
       a.probabilities!=b.probabilities||a.hidden!=b.hidden)return false;
  }
  return true;
}
} // namespace oneway
