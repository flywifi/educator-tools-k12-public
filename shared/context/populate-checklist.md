# Populate checklist — filling the Florida context stubs

The architecture + the 67-district log exist; this maps each **fillable field** to its **authoritative
source** so the data can be filled in (and kept current) without guessing. Verify on the official page
before writing a value; record the source. (Verified items so far: FAC 6A-1.09441 title; Orange/
Miami-Dade/Broward district virtual schools.)

## Per-district fields (`florida-districts.json → districts[]`)
| Field | Authoritative source |
|---|---|
| `superintendent` (volatile — verify each time) | https://www.fldoe.org/accountability/data-sys/school-dis-data/superintendents.stml |
| `board_governance` / school board | https://fsba.org/membership/school-boards/ |
| `district_virtual_school` (named) | https://www.fldoe.org/schools/school-choice/virtual-edu/directories/district-virtual-contacts.stml · https://www.fldoe.org/schools/school-choice/virtual-edu/district-resources/dis-franchises-of-fl-virtual-school.stml · https://www.flvs.net/schools-districts/resources/county-virtual-schools |
| `charter_schools_present` / charter directory | https://www.fldoe.org/schools/school-choice/charter-schools/ |
| `rules_and_norms` (pacing, calendars, mandates) | the district's own site + virtual memos: https://www.fldoe.org/schools/school-choice/virtual-edu/district-resources/memos.stml |
| school grade / accountability | https://www.fldoe.org/accountability/accountability-reporting/school-grades/index.stml |

## School-type fields (`school-types.json`)
| Type / field | Authoritative source |
|---|---|
| charter governance training + parent links | https://www.fldoe.org/schools/school-choice/charter-schools/charter-school-resources/governance-training.stml · https://www.fldoe.org/schools/school-choice/charter-schools/links-for-parents/ |
| district/FLVS virtual rules (s.1002.45) | https://www.fldoe.org/schools/school-choice/virtual-edu/district-resources/ |
| home education / other choice options | https://www.fldoe.org/schools/school-choice/other-school-choice-options/ |
| private-scholarship + home-ed scholarships (FTC, FES-EO, FES-UA, Hope, PEP) | https://www.fldoe.org/finance/financial-aid-scholarships/ |
| credit-bearing/FEFP courses (Course Code Directory) — FAC 6A-1.09441 | https://flrules.org/gateway/ruleNo.asp?ID=6A-1.09441 |

## Cross-cutting
| Topic | Source |
|---|---|
| educator certification (affects who can deliver) | https://www.fldoe.org/teaching/certification/ |
| State Board rules (FAC 6A, all chapters) | https://flrules.org/gateway/organization.asp?id=195 |

## How to fill (offline-friendly)
1. Pull the source page/doc; where it's a document, read it **offline** via docintel.
2. Write the verified value into the stub; set `status` and append the `sources` URL.
3. For district SOPs, drop files into the district's `sop_dir` and register them in the context
   contract's `sop_refs[]` (`sop-model.md`).
4. Keep `standards-updater` watching these sources so the data stays current (`monitoring_policy`).
