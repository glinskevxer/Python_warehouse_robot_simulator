# spikemaul

The track department of a shortline railroad, as a python package and a
console script. It keeps what the roadmaster keeps: what the railroad is made
of, what has been found on it, what the rule says to do about that, and what
the gangs are doing this week.

    pip install -e ".[dev]" -c constraints.txt
    spikemaul --book plains.sqlite3 init
    spikemaul --book plains.sqlite3 line add PLAINS Plains --end 120.00

## What it is for

Four questions get asked of a track department every day, and everything here
exists to answer one of them.

1. How fast can a train legally run over this piece of track today?
2. What did we find, what does the rule say we have to do, and by when?
3. Which inspections are due, which are late, and which piece of track is
   therefore not legal to operate over at all?
4. What is the gang doing next week, and what does it need on the ground?

## The command groups

| group | what it does |
| --- | --- |
| `init` | make a book, or bring an old one up to this schema |
| `status` | say what is in the book |
| `backup` | take a copy through sqlite and check the copy |
| `export` | write the book out as one csv per table |
| `line` | subdivisions, equations and segments |
| `curve` | curves, their elevation and the speed it buys |
| `turnout` | turnouts and their diverging speeds |
| `crossing` | grade crossings and their inventory numbers |
| `bridge` | structures and their load ratings |
| `person` | who is on the books and what they are designated for |
| `gang` | the gangs and their machines |
| `inspect` | recording inspections and asking what is due |
| `geometry` | loading a geometry run and reading it |
| `ties` | tie surveys and what they call for |
| `rail` | rail wear and the flaw testing cycle |
| `cwr` | the destress log and the heat call |
| `defect` | defect cards and the remedy each one requires |
| `order` | slow orders, the bulletin, the speed profile and what it costs |
| `work` | work orders and the week's plan |
| `report` | the morning page and the compliance page |
| `tonnage` | the monthly tonnage sheets |

`docs/commands.md` is the full reference and is generated from the script
itself. `docs/schema.md` is the shape of the book and is generated from the
migrations.

## The idea worth knowing before reading the code

A class of track is not a description of how good the track is. It is a
declaration of the limits the track is being held to, and every measurement is
judged against the row of the table that class names. When a measurement
fails, the remedy is usually to hold the track to the class it does meet,
which is a different row, so the same reading has two answers and which one
you get depends on what you asked.

That is the composition the whole package is built around. `docs/design.md`
has the rest of it.

## Running the checks

    python -m pytest -q
    python -m ruff check .
    python -m mypy
    python -m spikemaul.tools.check_layers

Every check under `spikemaul.tools` reads the tree it was installed from and
exits one if it has anything to say. CI runs all of them.
