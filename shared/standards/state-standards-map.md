# state-standards-map.md
## National standards overlay (approximate)
Which states follow **CCSS** (Math/ELA) and **NGSS** (Science) vs. their own sets. **Florida is the
only fully-populated state** (1/51); every other state is a **stub with room to fill in
later** — this is a deliberate placeholder, not a finished mapping. Machine-readable + editable slots:
`states.json`. Verified June 2026.

> **Caveat.** Stub rows are framework-level approximations and **must be verified on each state's DOE**
> (standards are periodically revised/rebranded). "CCSS-aligned" includes states that adopted CCSS and
> later revised/renamed it; "NGSS-based" means built on the K-12 Science Framework without full NGSS
> adoption.

## Big picture (verified)
- **CCSS (Math/ELA):** 41 states + DC + 4 territories + DoDEA adopted it. **Never adopted:** Alaska,
  Nebraska, Texas, Virginia. **Repealed/replaced with their own** (CCSS-influenced): Arizona, Florida,
  Georgia, Indiana, Oklahoma, South Carolina, Tennessee.
  [Common Core — standards in your state](https://www.thecorestandards.org/standards-in-your-state/).
- **NGSS (Science):** 20 states + DC adopted full NGSS; ~24 more use NGSS-based standards (~48 total on
  the K-12 Science Framework). Independent: Texas (TEKS), Florida (NGSSS), Virginia (SOL).
  [NGSS lead state partners](https://www.nextgenscience.org/lead-state-partners).
- This overlay: Math/ELA — {'CCSS-aligned': 40, 'independent': 11}; Science — {'NGSS-based': 27, 'NGSS': 21, 'independent': 3}.

## Populating a state (template — come back to this)
Only Florida is built out. To fill in another state later (no redesign needed — just fill the slots):
1. Confirm frameworks on the state DOE.
2. Create `shared/standards/<state>-best.md` with **verified** codes (mirror `florida-best.md`).
3. Optionally add `resources/<state>/` + `sources.json` (mirror `florida/`).
4. In `states.json`: set `status: populated`, fill `subjects[*]` (framework/source/example,
   `codes_verified`), set `adapter` + `resources_dir`.
5. Never invent codes — verify on the DOE (`protocols/standards-verification.md`).

## Per-state table (☐ stub = room to fill; verify on the state DOE)
| State | Status | Math/ELA | Science | State-specific set |
|---|---|---|---|---|
| Alabama | ☐ stub | CCSS-aligned | NGSS-based | — |
| Alaska | ☐ stub | independent | NGSS-based | Alaska Standards |
| Arizona | ☐ stub | independent | NGSS-based | Arizona Academic Standards |
| Arkansas | ☐ stub | CCSS-aligned | NGSS | — |
| California | ☐ stub | CCSS-aligned | NGSS | — |
| Colorado | ☐ stub | CCSS-aligned | NGSS-based | — |
| Connecticut | ☐ stub | CCSS-aligned | NGSS | — |
| Delaware | ☐ stub | CCSS-aligned | NGSS | — |
| District of Columbia | ☐ stub | CCSS-aligned | NGSS | — |
| Florida ⭐ | ✅ populated | independent | independent | B.E.S.T. (Math/ELA) + NGSSS (Science/SS) |
| Georgia | ☐ stub | independent | NGSS-based | Georgia Standards of Excellence |
| Hawaii | ☐ stub | CCSS-aligned | NGSS | — |
| Idaho | ☐ stub | CCSS-aligned | NGSS-based | — |
| Illinois | ☐ stub | CCSS-aligned | NGSS | — |
| Indiana | ☐ stub | independent | NGSS-based | Indiana Academic Standards |
| Iowa | ☐ stub | CCSS-aligned | NGSS | — |
| Kansas | ☐ stub | CCSS-aligned | NGSS | — |
| Kentucky | ☐ stub | CCSS-aligned | NGSS | — |
| Louisiana | ☐ stub | CCSS-aligned | NGSS-based | — |
| Maine | ☐ stub | CCSS-aligned | NGSS | — |
| Maryland | ☐ stub | CCSS-aligned | NGSS | — |
| Massachusetts | ☐ stub | CCSS-aligned | NGSS-based | — |
| Michigan | ☐ stub | CCSS-aligned | NGSS | — |
| Minnesota | ☐ stub | CCSS-aligned | NGSS-based | — |
| Mississippi | ☐ stub | CCSS-aligned | NGSS-based | — |
| Missouri | ☐ stub | CCSS-aligned | NGSS-based | — |
| Montana | ☐ stub | CCSS-aligned | NGSS-based | — |
| Nebraska | ☐ stub | independent | NGSS-based | Nebraska College & Career Ready Standards |
| Nevada | ☐ stub | CCSS-aligned | NGSS | — |
| New Hampshire | ☐ stub | CCSS-aligned | NGSS | — |
| New Jersey | ☐ stub | CCSS-aligned | NGSS | — |
| New Mexico | ☐ stub | CCSS-aligned | NGSS | — |
| New York | ☐ stub | CCSS-aligned | NGSS-based | — |
| North Carolina | ☐ stub | CCSS-aligned | NGSS-based | — |
| North Dakota | ☐ stub | CCSS-aligned | NGSS-based | — |
| Ohio | ☐ stub | CCSS-aligned | NGSS-based | — |
| Oklahoma | ☐ stub | independent | NGSS-based | Oklahoma Academic Standards |
| Oregon | ☐ stub | CCSS-aligned | NGSS | — |
| Pennsylvania | ☐ stub | CCSS-aligned | NGSS-based | — |
| Rhode Island | ☐ stub | CCSS-aligned | NGSS | — |
| South Carolina | ☐ stub | independent | NGSS-based | SC College- and Career-Ready |
| South Dakota | ☐ stub | CCSS-aligned | NGSS-based | — |
| Tennessee | ☐ stub | independent | NGSS-based | Tennessee Academic Standards |
| Texas | ☐ stub | independent | independent | TEKS |
| Utah | ☐ stub | CCSS-aligned | NGSS-based | — |
| Vermont | ☐ stub | CCSS-aligned | NGSS | — |
| Virginia | ☐ stub | independent | independent | SOL |
| Washington | ☐ stub | CCSS-aligned | NGSS | — |
| West Virginia | ☐ stub | CCSS-aligned | NGSS-based | — |
| Wisconsin | ☐ stub | CCSS-aligned | NGSS-based | — |
| Wyoming | ☐ stub | CCSS-aligned | NGSS-based | — |

## How the engine uses this
When a user names a state, look it up in `states.json`: if `status: populated` (currently only Florida),
use its adapter; otherwise use the framework classification as an **approximation**, tell the user it's
unverified, and verify on the state DOE (`protocols/standards-verification.md`).
