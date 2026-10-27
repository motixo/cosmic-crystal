#!/usr/bin/env python3
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('package_effects', ROOT / 'scripts/package_effects.py')
publisher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(publisher)


class PublisherTests(unittest.TestCase):
    def test_official_bundle_contains_all_glass_shader_sources(self):
        pack = publisher.bundle(5)
        self.assertEqual(pack['revision'], 5)
        self.assertEqual([e['id'] for e in pack['effects']], ['frosted', 'crystal', 'aero'])
        for effect in pack['effects'][1:]:
            self.assertEqual(effect['shader']['source'], (ROOT / 'shaders' / (effect['id'] + '.frag')).read_text())

    def test_community_metadata_and_shader_are_combined(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            sample = json.loads((ROOT / 'examples/prism.json').read_text())['effects'][0]
            source = sample['shader'].pop('source')
            (root / 'definition.json').write_text(json.dumps(sample))
            (root / 'prism.frag').write_text(source)
            pack = publisher.bundle(2, root / 'definition.json', 'my-pack', root)
            self.assertEqual(pack['id'], 'my-pack')
            self.assertEqual(pack['effects'][0]['shader']['source'], source)
            self.assertEqual(pack['effects'][0]['shader']['uniforms'], {'forge_prism': 'forge_prism_amount'})

    def test_missing_custom_shader_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'definition.json').write_text('{"id":"missing","preview":"aero"}')
            with self.assertRaises(ValueError):
                publisher.bundle(1, root / 'definition.json', 'my-pack', root)

    def test_new_effect_files_join_the_official_release_pack(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'effects').mkdir()
            (root / 'shaders').mkdir()
            (root / 'effects.json').write_text('[]')
            effect = json.loads((ROOT / 'examples/prism.json').read_text())['effects'][0]
            source = effect['shader'].pop('source')
            (root / 'effects/prism.json').write_text(json.dumps(effect))
            (root / 'shaders/prism.frag').write_text(source)
            with patch.object(publisher, 'ROOT', root):
                pack = publisher.bundle(2)
            self.assertEqual(pack['id'], 'cosmic-glass')
            self.assertEqual(pack['effects'][0]['id'], 'prism')
            self.assertEqual(pack['effects'][0]['shader']['source'], source)
