"""Explicit graph rebuild from the pinned notebook mappings and raw vocabulary.

This is a reviewed authoring operation, not part of CI. Inspect/version TTL diffs.
"""
from hotel_cancel.config import load_config
from hotel_cancel.data import load_bookings,separate_outcome
from hotel_cancel.knowledge import build_reference,build_extended,KB_DIR

bookings,_=separate_outcome(load_bookings(load_config(),use_cache=False))
reference=build_reference(bookings)
assert len(reference)==607,'Reference vocabulary differs; inspect raw data and mapping source'
reference.serialize(KB_DIR/'reference.ttl',format='turtle')
extended=build_extended(reference);extended.serialize(KB_DIR/'hotel.ttl',format='turtle')
print(f'Rebuilt reference ({len(reference)} triples) and extension ({len(extended)} triples). Review changes before committing.')
