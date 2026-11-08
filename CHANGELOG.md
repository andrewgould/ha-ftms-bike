# Changelog

Versions follow [semantic versioning](https://semver.org/). The version in
`manifest.json` is what HACS installs, and each release tag must match it.

## 1.2.0

- **Totals**, like a smart plug's energy counter: total distance, work (power
  over time, in kJ), calories and ride time. They count every session for good
  and survive restarts, so Home Assistant's statistics can show them per day,
  week or month.
- **Ride** figures for the latest session: distance, work, calories, time and
  average power. They restart when a session starts and keep the last ride's
  figures until the next.
- Both see through the console's own counters dropping back to zero, which
  happens whenever an app starts or ends a workout.

## 1.1.0

- **Watch only** option: the bike is never sent a command, so an app running
  the ride keeps control while Home Assistant reads along. The target controls
  go away.
- **Start sessions automatically** option: connects whenever the bike is heard.
  A session switched off by hand stays off until the console goes to sleep, and
  one that ended for lack of pedalling looks again 5 minutes later.
- Together they let Home Assistant log every ride on a console with a spare
  Bluetooth module, like the Lifespan SM-810, while Kinomap uses the other one.

## 1.0.0

First release.

- Connects only during a session started from the **Session** switch, so
  training apps keep the bike the rest of the time. Sessions end when switched
  off, when the bike disconnects, or after 5 minutes without pedalling.
- Speed, cadence, power, resistance, distance, calories, elapsed time and
  heart rate.
- Target resistance in the console's levels, and target power.
- A **Resistance scale** option for consoles that don't read the resistance
  command as the standard says.
