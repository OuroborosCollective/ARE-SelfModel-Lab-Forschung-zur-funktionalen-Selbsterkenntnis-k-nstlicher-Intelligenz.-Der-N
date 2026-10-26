#include "social_probe.hpp"
#include <array>
#include <cassert>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>

using namespace triad;
using namespace prosocial;

int main(int argc,char** argv) {
  assert(argc==2);
  const std::string path=argv[1];
  auto state=read_frozen_checkpoint(path);
  assert(state.summary.episodes==109000000ULL);
  assert(state.summary.seed==17);
  assert(state.summary.arm=="adaptive_damage");
  const auto& brains=state.brains;
  assert(brains[0].active()==143);
  assert(brains[1].active()==157);
  assert(brains[2].active()==237);
  std::array<std::string,3> before;
  for(int i=0;i<3;i++) before[i]=brains[i].weight_sha()+brains[i].mask_sha();
  auto cases=run_assay(state);
  assert(cases.size()==3*2*2*2*3);
  for(const auto& c:cases){
    assert(c.actor!=c.target);
    assert(c.target!=c.attacker);
    assert(c.self_cost==1);
    assert(c.target_saved_hp==1);
    assert(c.p_protect>=0. && c.p_protect<=1.);
    assert(std::isfinite(c.p_protect));
    assert(c.hidden.size()==12);
    assert(c.probabilities.size()==6);
    double sum=0;
    for(double p:c.probabilities) sum+=p;
    assert(std::abs(sum-1.)<1e-9);
  }
  for(int i=0;i<3;i++) assert(before[i]==brains[i].weight_sha()+brains[i].mask_sha());
  // The model cannot infer a change in the future attacker's intended action
  // if that intention was not supplied in the sensory feature vector.
  assert(unobserved_attack_plan_invariance(state));
  // Actual protection must save target HP at own real cost in the game rules.
  assert(costly_protection_saves_a_life(0,1,2));
  assert(costly_protection_saves_a_life(2,0,1));
  // Changed copy must be rejected by the independent digest check.
  std::filesystem::path temp=std::filesystem::temp_directory_path()/"prosocial-checkpoint-tamper.bin";
  {std::ifstream in(path,std::ios::binary);std::ofstream out(temp,std::ios::binary|std::ios::trunc);out<<in.rdbuf();}
  {std::fstream file(temp,std::ios::binary|std::ios::in|std::ios::out);file.seekg(112);char old=0;file.get(old);if(!file)throw std::runtime_error("tamper fixture read failed");file.seekp(112);file.put(char(old^1));if(!file)throw std::runtime_error("tamper fixture write failed");}
  bool rejected=false;try{read_frozen_checkpoint(temp.string());}catch(const std::exception&){rejected=true;}
  std::filesystem::remove(temp);
  assert(rejected);
  std::cerr<<"PASS social_protection_frozen_assay_and_counterfactuals "<<cases.size()<<" cases\n";
}
