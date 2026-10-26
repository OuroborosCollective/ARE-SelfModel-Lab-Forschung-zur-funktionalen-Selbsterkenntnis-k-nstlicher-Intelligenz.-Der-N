#include "one_way_rescue.hpp"
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>
#include <cstdint>

static void arr(std::ostream& o,const double* ptr,int n){o<<'[';for(int i=0;i<n;i++){if(i)o<<',';o<<ptr[i];}o<<']';}
int main(int argc,char** argv){
  try{
    if(argc!=6 && argc!=7)throw std::invalid_argument("usage: probe 109m.bin expected_sha 200m.bin expected_sha result.json [samples_per_case]");
    const uint64_t samples_per_case=argc==7?std::stoull(argv[6]):500000ULL;
    if(samples_per_case<1 || samples_per_case>2000000ULL)throw std::invalid_argument("samples_per_case outside 1..2000000");
    const std::string actual_109=prosocial::sha_of_file(argv[1]);
    const std::string actual_200=prosocial::sha_of_file(argv[3]);
    if(actual_109!=argv[2] || actual_200!=argv[4] ||
        actual_109!="01e0c495a110689fce4c87420a01e948a27952924575d543fa5bda136e2c3820" ||
        actual_200!="a094d818be545d2f7c06c50c0ee7aacdee4ac60a72cbdaddf35f15d3ed920d92")
      throw std::runtime_error("checkpoint digest untrusted or mismatched");
    const auto earlier=oneway::evaluate(argv[1],109000000ULL);
    const auto later=oneway::evaluate(argv[3],200000000ULL);
    if(!oneway::paired_attack_invariance(earlier)||!oneway::paired_attack_invariance(later))
      throw std::runtime_error("hidden future attack information leaked into brain");
    std::ofstream out(argv[5],std::ios::out|std::ios::trunc);
    if(!out)throw std::runtime_error("cannot create assay result");
    out<<std::setprecision(17);
    out<<"{\"schema\":\"are-selfmodel-oneway-costly-protection-1\",\"input_warning_visible_to_old_model\":false,\"reward_or_training_during_holdout\":false,\"case_count\":288,\"samples_per_case\":"<<samples_per_case<<",\"studies\":[";
    const std::array<const oneway::Study*,2> studies{&earlier,&later};
    for(size_t k=0;k<2;k++){
      if(k)out<<',';
      const auto& s=*studies[k];
      double probability_mass=0.,life_saved_expected=0.;int genuine_cases=0;
      uint64_t sampled_shields=0,sampled_saves=0,sampled_unneeded_shields=0;
      for(const auto& row:s.rows){probability_mass+=row.p_shield;if(row.prevented_death){genuine_cases++;life_saved_expected+=row.p_shield;}}
      out<<"{\"episodes\":"<<s.summary.episodes<<",\"original_checkpoint_sha256\":\""<<s.checkpoint_sha256<<"\",\"brain_weights_unchanged\":"<<(s.brains_unchanged?"true":"false")
         <<",\"mean_shield_probability\":"<<(probability_mass/s.rows.size())<<",\"sum_expected_lives_saved\":"<<life_saved_expected<<",\"true_rescue_cases\":"<<genuine_cases<<",\"active\":[";
      for(int a=0;a<3;a++){if(a)out<<',';out<<s.brains[a].active();}
      out<<"],\"rows\":[";
      for(size_t i=0;i<s.rows.size();i++){
        if(i)out<<',';
        const auto& row=s.rows[i];
        // Each sampled action is drawn from the original complete six-action policy.
        // Trial outcomes are computed from the certified resolve() counterfactual.
        triad::FastRng r(triad::seedmix(20261026ULL,row.actor,static_cast<int>(i+144*k)));
        uint64_t selected=0, saved=0, unneeded=0;
        for(uint64_t sample=0;sample<samples_per_case;sample++){
          const double x=r.uniform();double total=0.;int chosen=-1;
          for(int a=0;a<6;a++){
            total+=row.probabilities[a];
            if(row.probabilities[a]>0 && x<=total){chosen=a;break;}
          }
          if(chosen<0)throw std::runtime_error("sampled action out of range");
          if(chosen==3+row.target){
            selected++;
            if(row.prevented_death)saved++;
            else if(!row.attacker_hits_target)unneeded++;
          }
        }
        sampled_shields+=selected;sampled_saves+=saved;sampled_unneeded_shields+=unneeded;
        out<<"{\"actor\":"<<row.actor<<",\"target\":"<<row.target<<",\"attacker\":"<<row.attacker
           <<",\"self_hp\":"<<row.self_hp<<",\"target_hp\":"<<row.target_hp<<",\"memory_mode\":"<<row.memory_mode
           <<",\"attacker_hits_target\":"<<(row.attacker_hits_target?"true":"false")
           <<",\"prevented_death_if_shield\":"<<(row.prevented_death?"true":"false")
           <<",\"helper_cost_if_shield\":"<<row.helper_cost
           <<",\"target_hp_delta_if_shield\":"<<row.target_delta_on_shield
           <<",\"target_hp_if_shield\":"<<row.after_shield_hp<<",\"target_hp_if_attack\":"<<row.after_attack_hp
           <<",\"p_shield\":"<<row.p_shield<<",\"sampled_shield_actions\":"<<selected<<",\"sampled_actual_rescues\":"<<saved<<",\"sampled_sham_shields\":"<<unneeded<<",\"probabilities\":";
        arr(out,row.probabilities.data(),6);
        out<<",\"hidden\":";arr(out,row.hidden.data(),12);
        out<<",\"weights_sha256\":\""<<row.actor_weights_sha256<<"\",\"mask_sha256\":\""<<row.actor_mask_sha256<<"\"}";
      }
      out<<"],\"sampled_shield_actions\":"<<sampled_shields<<",\"sampled_actual_rescues\":"<<sampled_saves<<",\"sampled_sham_shields\":"<<sampled_unneeded_shields<<"}";
    }
    out<<"],\"design\":\"frozen_predecision_one_way_costly_rescue_and_sham_continuation\",\"interpretation\":\"exact_action_probabilities_not_sampled_decisions\"}\n";
    out.close();if(!out)throw std::runtime_error("cannot finalize result");
    std::cout<<"ONE_WAY_ASSAY_OK cases=288 checkpoints=109000000,200000000 sha109="<<actual_109<<" sha200="<<actual_200<<"\n";
  }catch(const std::exception& err){std::cerr<<"ERROR: "<<err.what()<<"\n";return 1;}
}
