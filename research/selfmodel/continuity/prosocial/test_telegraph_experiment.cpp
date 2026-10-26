#define ARE_TELEGRAPH_LIB_ONLY
#include "telegraph_experiment.cpp"
#include <cassert>
#include <iostream>
int main(){
 using namespace telegraph;
 Head h(true);train(h,101,40000);
 const Scenario attack{{3,1,true},true},miss{{3,1,true},false};
 assert(h.shield(attack.pre)==h.shield(miss.pre));
 assert(resolve(attack,true).rescue);
 assert(resolve(attack,true).helper_hp_spent==1);
 assert(!resolve(attack,false).rescue);
 assert(resolve(miss,true).unnecessary);
 assert(!resolve(miss,false).unnecessary);
 assert(h.shield({3,1,true}));
 assert(!h.shield({3,1,false}));
 assert(!h.shield({3,8,true}));
 assert(!h.shield({1,1,true}));
 Head again(true);train(again,101,40000);
 assert(h.weights==again.weights);
 Head blind(false);train(blind,101,40000);
 const auto one=evaluate(h,blind,20261026,20000);
 const auto two=evaluate(h,blind,20261026,20000);
 assert(one.learned.rescues==two.learned.rescues);
 assert(one.learned.shams==two.learned.shams);
 assert(one.learned.utility>one.always.utility);
 assert(one.learned.utility>one.scrambled.utility);
 assert(one.learned.rescues<one.always.rescues);
 assert(one.learned.shams<one.always.shams);
 const auto shifted=evaluate(h,blind,20261027,20000,0.65,0.2);
 assert(shifted.learned.rescues<shifted.always.rescues);
 assert(shifted.learned.utility!=one.learned.utility);
 bool rejected=false;
 try{FastRng bad(1);(void)generate(bad,1.5);}catch(const std::invalid_argument&){rejected=true;}
 assert(rejected);
 std::cout<<"TESTS_PASS: causal_input/cost/benefit/training/replay/negative_control/prior_shift\n";
}
