# Changelog

## Unreleased

Nothing yet.

## 0.1.0

The first version that does the whole job rather than part of it.

- The railroad itself: subdivisions with their equations, segments held to a
  class, curves with the elevation they carry, turnouts, crossings and
  structures.
- Geometry runs loaded from the contractor's csv, marked up from the curve
  register and read against the class each segment is held to, warp included.
- Tie surveys counted per rail length, with the count rule, the run rule and
  the joint rule kept apart.
- Rail wear projected against tonnage, and the flaw testing cycle with its two
  clocks.
- Welded rail: the destress log, and the heat call with its bands.
- Defect cards that carry the class the condition meets, and the remedial
  action worked out against the class the track carries today.
- Slow orders, the bulletin, the speed profile and what the restrictions cost
  in minutes.
- The inspection program, including the designation that makes an inspection
  count and the one that lapsed.
- Work orders, the week's plan and the material that has to be on the ground.
- The morning page, the compliance page, the rail page, the speed profile, the
  week sheet and the records audit.
- A console script over all of it, a book that carries its own schema number,
  a backup through sqlite, a csv export and one search across every register.
