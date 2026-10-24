import json,math,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Scripts'))
import v25_contracts as c
import prepare_v25
ROOT=Path(__file__).resolve().parents[1]

class V25Contracts(unittest.TestCase):
    def state(self):
        x=[0.]*64
        for i in (16,19,24,25,26,31,39,48,53):x[i]=1
        return x
    def test_exact_schema_and_reserved_outputs(self):
        self.assertEqual(len(c.FEATURES),64);self.assertEqual(len(set(c.FEATURES)),64)
        self.assertEqual(len(c.ACTIONS),48)
        self.assertFalse(any(c.valid_actions(self.state())[9:]))
    def test_unassigned_job_cannot_travel_or_work(self):
        x=self.state();x[48]=0;x[32]=1;m=c.valid_actions(x)
        self.assertFalse(m[1]);self.assertFalse(m[2])
    def test_rain_interrupts_work_and_selects_available_shelter(self):
        x=self.state();x[2]=1;x[32]=1;m=c.valid_actions(x)
        self.assertFalse(m[1] or m[2]);self.assertEqual(c.baseline(x,m),4)
        x[24]=0;self.assertNotEqual(c.baseline(x),4)
    def test_passage_and_work_reservations(self):
        slots=c.Reservations();self.assertTrue(slots.acquire('lane','tractor'))
        self.assertFalse(slots.acquire('lane','resident_00'));slots.release('tractor')
        self.assertTrue(slots.acquire('lane','resident_00'))
        x=self.state();x[28]=1;self.assertEqual(c.baseline(x),7)
        x[28]=0;x[32]=1;x[53]=0;self.assertFalse(c.valid_actions(x)[2])
    def test_failed_invalid_and_low_confidence_inference_fallbacks(self):
        mask=c.valid_actions(self.state());fallback=c.baseline(self.state(),mask)
        for logits in (None,[float('nan')]*48,[float('inf')]*48,[0.]*48):
            self.assertEqual(c.select_action(logits,mask,fallback),fallback)
        self.assertEqual(c.select_action([5.]*48,[False]*48,8),0)
        scores=[-1.]*48;scores[47]=100;self.assertNotEqual(c.select_action(scores,mask,fallback),47)
    def test_utf8_byte_limits_and_combining_signs(self):
        text='ਸਤ ਸ੍ਰੀ ਅਕਾਲ ਜੀ।';self.assertEqual(c.normalize_text(text),text)
        with self.assertRaises(ValueError):c.normalize_text('ਅ'*86)
        self.assertEqual(c.normalize_text('a'*256),'a'*256)
    def test_nonfinite_state_rejected_and_ranges_clamped(self):
        with self.assertRaises(ValueError):c.sanitize([float('nan')]*64)
        with self.assertRaises(ValueError):c.sanitize([0.]*63)
        self.assertEqual(c.sanitize([-1,2]+[0.]*62)[:2],[0,1])
    def test_scene_provenance_geometry_and_identity_contracts(self):prepare_v25.validate()
    def test_deployed_budget_and_export_hash(self):
        import hashlib,onnx,numpy as np
        manifest=json.loads((ROOT/'Assets/Models/npc_model_manifest.json').read_text())
        total=0
        for item in manifest['deployed_models']:
            path=ROOT/'Assets/Models'/item['file'];self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),item['sha256'])
            model=onnx.load(path);onnx.checker.check_model(model)
            self.assertEqual(sum(int(np.prod(t.dims)) for t in model.graph.initializer),item['physical_initializer_values'])
            total+=item['unique_parameters']
        self.assertEqual(total,121520);self.assertLessEqual(total,1000000)
        self.assertFalse(manifest['intent_enabled'] or manifest['micro_decoder_enabled'])
    def test_unreviewed_dialogue_cannot_be_mistaken_for_reviewed_audio(self):
        for row in (ROOT/'Assets/Dialogue/punjabi_lines.jsonl').read_text(encoding='utf-8').splitlines():
            line=json.loads(row);self.assertEqual(line['review_status'],'draft_unreviewed')
            self.assertIsNone(line['reviewer']);self.assertIsNone(line['audio_id'])

if __name__=='__main__':unittest.main()
