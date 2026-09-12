"""Declared offline uncertainty; never used to supply a real research decision."""
from report_profile import ASSESSMENT_AXES


def cutoff_decision(coverage):
    dimensions = [c['dimension'] for c in coverage]
    ids = list(dict.fromkeys(fid for c in coverage for fid in
                           (c['finding_ids'] or ['gap-' + c['dimension']])))
    return {
        'requirements': [],
        'verdict': {'kind': 'insufficient_evidence', 'scope': 'SYNTHETIC supplied evidence only',
                    'finding_ids': ids, 'requirement_ids': []},
        'synthesis': [{'axis': axis, 'conclusion': 'SYNTHETIC: evidence is incomplete for this assessment.',
                       'finding_ids': ids, 'coverage_dimensions': dimensions} for axis in ASSESSMENT_AXES],
        'actions': [{'id': 'resolve', 'kind': 'investigate', 'action': 'Inspect the unresolved synthetic controls.',
                     'reason': 'The fixture supplies identity but no completed control review.',
                     'finding_ids': ids, 'coverage_dimensions': dimensions, 'requirement_ids': [],
                     'changes_view_if': 'Source and authority evidence could establish bounded controls or a harmful capability.'}]}
