# How this is put together

## The layers

    units       milepost arithmetic, speed, temperature, tonnage, curvature
    standards   the class tables and every limit read off them
    model       the records, which validate themselves and know nothing else
    geometry    reading a run against a class
    ties        tie condition, per rail length
    cwr         neutral temperature and the heat call
    rail        wear and the flaw testing cycle
    orders      the speed profile, the bulletin and the running time
    program     what is due and what is late
    work        turning what was found into what the gang does
    store       the book, the migrations and one register per record
    loading     the files other people's machines hand over
    report      the pages the office prints
    cli         the console script, the only part that prints
    tools       the checks CI runs against this tree

Nothing imports upwards. `spikemaul.tools.check_layers` holds the table and
fails the build when something does.

## The rules that decide what other rules measure

- **The class sets the limits, and the limits set the class.**
  `spikemaul.geometry.assessment` reads a run against the class a segment is
  held to, works out the class every reading does support, and hands both to
  `spikemaul.standards.remedial`. The walk settles on the first step, because
  what a reading supports does not depend on what it was read against, and
  there is a test that says so.
- **A curve carries its own speed.** `spikemaul.model.curve` works it off the
  elevation and the unbalance, and `spikemaul.orders.governing` takes the
  lowest cap at each foot of railroad rather than assuming the class speed.
- **Warp is a difference over a window.** `spikemaul.geometry.warp` yields
  every pair inside it, so one bad station makes several findings, which is
  what the rule measures.
- **Ties are counted per rail length and two of the three rules are about
  position.** `spikemaul.ties.condition` holds the count, the run and the
  joint rule apart and takes the lowest.
- **A missed inspection is not a defect and it is worse.**
  `spikemaul.program.compliance` will not count an inspection by somebody
  whose designation had lapsed, and reports it separately rather than dropping
  it.
- **Deadlines are kept on the clock the rule counts in.**
  `spikemaul.standards.remedial` refuses to compare a deadline in trains with
  one in days.

## The decisions that are not obvious

- **Mileposts are not a coordinate system.** `spikemaul.units.chainage` holds
  the equations, so distance is asked for rather than subtracted.
- **The day always arrives as an argument.** `spikemaul.cli.clock` is the only
  module that reads the system clock, and `spikemaul.tools.check_clock` keeps
  it that way, so a page reprinted in November says what it said in May.
- **The book is autocommit and a transaction is asked for.**
  `spikemaul.store.book` says why, and the reason is that every register write
  was silently uncommitted until a test read it back through a second
  connection.
- **Records validate themselves on the way in.** A `spikemaul.model` record
  that exists is one that made sense, so nothing downstream re-checks it.
