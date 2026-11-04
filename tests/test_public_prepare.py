import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

PATH=Path(__file__).resolve().parents[1]/'examples/cheng-adaptive/prepare.py'
spec=importlib.util.spec_from_file_location('public_prepare',PATH);prepare=importlib.util.module_from_spec(spec);spec.loader.exec_module(prepare)

class PrepareTests(unittest.TestCase):
    def test_prepare_preserves_inputs_and_does_not_start_study(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);inputs=root/'inputs';inputs.mkdir();target=root/'new'
            (inputs/'images_fp16.npy').write_bytes(b'fixture: image interpretation belongs to trainer')
            records=[{'index':0,'patient_id':'a','label':0,'split':'train'},{'index':1,'patient_id':'b','label':1,'split':'val'}]
            (inputs/'records.json').write_text(json.dumps(records));(inputs/'input_manifest.json').write_text('{}')
            result=subprocess.CompletedProcess([],0,stdout='{"resnet18":{"parameters":1000}}',stderr='')
            with patch.object(prepare.subprocess,'run',return_value=result):out=prepare.prepare(target,inputs,sys.executable)
            self.assertFalse(out['research_started']);self.assertFalse((target/'executor/study.sqlite').exists())
            self.assertEqual((inputs/'records.json').read_bytes(),(target/'inputs/records.json').read_bytes())
            seal=json.loads((target/'executor/seal.json').read_text())
            self.assertEqual(seal['files']['inputs/records.json'],prepare.sha(inputs/'records.json'))
            with self.assertRaisesRegex(ValueError,'exists'):prepare.prepare(target,inputs,sys.executable)

    def test_test_rows_and_patient_leakage_are_rejected_before_writing(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);inputs=root/'inputs';inputs.mkdir()
            (inputs/'images_fp16.npy').write_bytes(b'fixture');(inputs/'input_manifest.json').write_text('{}')
            for records in [[{'index':0,'patient_id':'a','label':0,'split':'test'}],
                [{'index':0,'patient_id':'a','label':0,'split':'train'},{'index':1,'patient_id':'a','label':1,'split':'val'}]]:
                (inputs/'records.json').write_text(json.dumps(records))
                with self.assertRaises(ValueError):prepare.prepare(root/'new',inputs,sys.executable)
                self.assertFalse((root/'new').exists())

if __name__=='__main__':unittest.main()
