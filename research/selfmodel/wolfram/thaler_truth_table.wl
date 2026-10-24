(* Independent check of Thaler 1995, Figure 1 and lesion of the -2 link.
   This confirms binary circuit arithmetic, not subjective experience. *)
ClearAll[gedankenOutput, table, expected];
gedankenOutput[x_Integer, y_Integer, inhibition_: True] := Module[
  {hidden = Boole[x + y > 3/2]},
  Boole[x + y - If[inhibition, 2 hidden, 0] > 1/2]
];
table = Flatten[Table[
  {x, y, gedankenOutput[x, y], gedankenOutput[x, y, False]},
  {x, 0, 1}, {y, 0, 1}
], 1];
expected = {{0, 0, 0, 0}, {0, 1, 1, 1}, {1, 0, 1, 1}, {1, 1, 0, 1}};
If[table =!= expected, Print["FAILED: exact truth table mismatch"]; Abort[]];
<|"truthTable" -> table, "xorCorrect" -> True,
  "damageMisclassifies11" -> (gedankenOutput[1, 1] == 0 && gedankenOutput[1, 1, False] == 1),
  "subjectiveExperienceInferred" -> False|>
