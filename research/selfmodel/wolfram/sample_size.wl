(* ILLUSTRATIVE ONLY. Assumes two independent proportions and simple normal
   approximation. Correlated prompts, repeated models or clustered trials
   require a different, preregistered design and power simulation. *)
ClearAll[p1, p0, alpha, power, pBar, zAlpha, zPower, nPerArm];
p1 = 0.20;
p0 = 0.10;
alpha = 0.05;
power = 0.80;
pBar = (p1 + p0)/2;
zAlpha = InverseCDF[NormalDistribution[0, 1], 1 - alpha/2];
zPower = InverseCDF[NormalDistribution[0, 1], power];
nPerArm = Ceiling[((zAlpha Sqrt[2 pBar (1 - pBar)] +
      zPower Sqrt[p1 (1 - p1) + p0 (1 - p0)])^2)/(p1 - p0)^2];
Print[<|"illustrative_n_per_arm" -> nPerArm,
  "assumption" -> "independent Bernoulli trials; two arms only",
  "not_verified_model_runs" -> True|>];
