import json
import tempfile
import unittest
from pathlib import Path
from audit_observer import audit

class AuditTests(unittest.TestCase):
    def test_fake_input_or_invalid_probabilities_are_rejected(self):
        row={"schema":"are-selfmodel-observer-1","phase":"pre_decision","episode":0,"agent":0,
             "input":[0.]*15,"hidden":[0.]*12,"probabilities":[1.,0.,0.,0.,0.,0.],"action":0,
             "weights_sha256":"a"*64,"mask_sha256":"b"*64,"short_term_trace_count":1}
        post={"schema":"are-selfmodel-observer-1","phase":"post_update","episode":0,"agents":
              [{"id":i,"active":252,"lesions":0} for i in range(3)]}
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'test.jsonl'
            for values in (([row,post], "incomplete"),([dict(row,agent=0),dict(row,agent=1),dict(row,agent=2),post], None)):
                path.write_text(''.join(json.dumps(v)+'\n' for v in values[0]))
                if values[1]:
                    with self.assertRaises(ValueError):audit(path)
                else:
                    result=audit(path)
                    self.assertEqual(result['sampled_pre_decision'],3)
            row['probabilities']=[0.,0.,0.,0.,0.,0.]
            path.write_text(''.join(json.dumps(v)+'\n' for v in (row,post)))
            with self.assertRaises(ValueError):audit(path)

if __name__=='__main__':unittest.main()
