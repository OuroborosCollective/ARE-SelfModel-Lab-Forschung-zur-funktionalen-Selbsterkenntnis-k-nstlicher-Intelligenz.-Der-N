#include "one_way_rescue.hpp"
#include <cassert>
#include <cmath>
#include <iostream>

int main(int argc, char **argv) {
  assert(argc==3);
  auto earlier = oneway::evaluate(argv[1],109000000ULL);
  auto later = oneway::evaluate(argv[2],200000000ULL);
  assert(earlier.rows.size()==144);
  assert(later.rows.size()==144);
  assert(earlier.summary.episodes==109000000ULL);
  assert(later.summary.episodes==200000000ULL);
  assert(later.summary.wins[2]>earlier.summary.wins[2]);
  for(const auto* study : {&earlier, &later}){
    assert(study->observability_warning_visible==false);
    assert(study->brains_unchanged);
    for(const auto& row : study->rows){
      assert(row.actor>=0 && row.actor<3);
      assert(row.target>=0 && row.target<3 && row.target!=row.actor);
      assert(row.attacker!=row.actor && row.attacker!=row.target);
      assert(row.p_shield>=0 && row.p_shield<=1 && std::isfinite(row.p_shield));
      assert(std::abs(row.p_sum-1.)<1e-10);
      assert(row.helper_cost==1);
      assert(row.target_delta_on_shield==(row.attacker_hits_target?1:0));
      assert(row.prevented_death==(row.attacker_hits_target && row.target_hp==1));
      if(row.prevented_death)assert(row.after_shield_hp==1 && row.after_attack_hp==0);
      if(!row.attacker_hits_target)assert(!row.prevented_death);
    }
  }
  assert(oneway::paired_attack_invariance(later));
  assert(later.brains[0].active()==64);
  assert(later.brains[1].active()==79);
  assert(later.brains[2].active()==237);
  std::cerr << "PASS one-way rescue: two authentic checkpoints, 288 cases, full causal resolution\n";
}
