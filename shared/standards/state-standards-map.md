# state-standards-map.md
## National standards overlay (approximate)
A broad map of which states follow **CCSS** (Math/ELA) and **NGSS** (Science) vs. their own sets.
**Florida is the deep, fully-supported state** — see `florida-best.md` + `resources/florida/`. Everything
here is a *framework-level approximation* and must be verified on each state's DOE, since standards are
periodically revised or rebranded. Machine-readable: `states.json`. Verified June 2026.

> **Caveat.** "CCSS-aligned" includes states that adopted Common Core and later revised or **renamed**
> it (e.g., many "repealed" states kept CCSS-influenced standards). "NGSS-based" means built on the
> *Framework for K-12 Science Education* without full NGSS adoption. Confirm specifics on the state DOE.

## Big picture (verified)
- **CCSS (Math/ELA):** 41 states + DC + 4 territories + DoDEA adopted it. **Never adopted:** Alaska,
  Nebraska, Texas, Virginia. **Repealed/replaced with their own** (CCSS-influenced): Arizona, Florida,
  Georgia, Indiana, Oklahoma, South Carolina, Tennessee. Many adopters have since revised/rebranded.
  Source: [Common Core — standards in your state](https://www.thecorestandards.org/standards-in-your-state/).
- **NGSS (Science):** **20 states + DC adopted full NGSS**; ~24 more use **NGSS-based** standards
  (≈48 states total built on the K-12 Science Framework). Distinct independent science sets include
  Texas (TEKS), Florida (NGSSS), Virginia (SOL).
  Source: [NGSS lead state partners](https://www.nextgenscience.org/lead-state-partners).
- This overlay: Math/ELA — {'CCSS-aligned': 40, 'independent': 11}; Science — {'NGSS-based': 27, 'NGSS': 21, 'independent': 3}.

## Per-state table (approximate; verify on the state DOE)
| State | Math/ELA | Science | State-specific set |
|---|---|---|---|
| Alabama | CCSS-aligned | NGSS-based | — |
| Alaska | independent | NGSS-based | Alaska Standards |
| Arizona | independent | NGSS-based | Arizona Academic Standards |
| Arkansas | CCSS-aligned | NGSS | — |
| California | CCSS-aligned | NGSS | — |
| Colorado | CCSS-aligned | NGSS-based | — |
| Connecticut | CCSS-aligned | NGSS | — |
| Delaware | CCSS-aligned | NGSS | — |
| District of Columbia | CCSS-aligned | NGSS | — |
| Florida ⭐ | independent | independent | B.E.S.T. (Math/ELA) + NGSSS (Science/SS) |
| Georgia | independent | NGSS-based | Georgia Standards of Excellence |
| Hawaii | CCSS-aligned | NGSS | — |
| Idaho | CCSS-aligned | NGSS-based | — |
| Illinois | CCSS-aligned | NGSS | — |
| Indiana | independent | NGSS-based | Indiana Academic Standards |
| Iowa | CCSS-aligned | NGSS | — |
| Kansas | CCSS-aligned | NGSS | — |
| Kentucky | CCSS-aligned | NGSS | — |
| Louisiana | CCSS-aligned | NGSS-based | — |
| Maine | CCSS-aligned | NGSS | — |
| Maryland | CCSS-aligned | NGSS | — |
| Massachusetts | CCSS-aligned | NGSS-based | — |
| Michigan | CCSS-aligned | NGSS | — |
| Minnesota | CCSS-aligned | NGSS-based | — |
| Mississippi | CCSS-aligned | NGSS-based | — |
| Missouri | CCSS-aligned | NGSS-based | — |
| Montana | CCSS-aligned | NGSS-based | — |
| Nebraska | independent | NGSS-based | Nebraska College & Career Ready Standards |
| Nevada | CCSS-aligned | NGSS | — |
| New Hampshire | CCSS-aligned | NGSS | — |
| New Jersey | CCSS-aligned | NGSS | — |
| New Mexico | CCSS-aligned | NGSS | — |
| New York | CCSS-aligned | NGSS-based | — |
| North Carolina | CCSS-aligned | NGSS-based | — |
| North Dakota | CCSS-aligned | NGSS-based | — |
| Ohio | CCSS-aligned | NGSS-based | — |
| Oklahoma | independent | NGSS-based | Oklahoma Academic Standards |
| Oregon | CCSS-aligned | NGSS | — |
| Pennsylvania | CCSS-aligned | NGSS-based | — |
| Rhode Island | CCSS-aligned | NGSS | — |
| South Carolina | independent | NGSS-based | SC College- and Career-Ready |
| South Dakota | CCSS-aligned | NGSS-based | — |
| Tennessee | independent | NGSS-based | Tennessee Academic Standards |
| Texas | independent | independent | TEKS |
| Utah | CCSS-aligned | NGSS-based | — |
| Vermont | CCSS-aligned | NGSS | — |
| Virginia | independent | independent | SOL |
| Washington | CCSS-aligned | NGSS | — |
| West Virginia | CCSS-aligned | NGSS-based | — |
| Wisconsin | CCSS-aligned | NGSS-based | — |
| Wyoming | CCSS-aligned | NGSS-based | — |

## How the engine uses this
When a user names a state, look it up in `states.json`: if `independent`/named (e.g., Florida, Texas,
Virginia), prefer that set; otherwise default to **CCSS** (Math/ELA) + **NGSS/NGSS-based** (Science),
and **verify on the state DOE** (`protocols/standards-verification.md`). Only **Florida** is fully
populated today; other states follow the `state-standards-model.md` template as they're built out.
