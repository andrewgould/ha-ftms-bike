# Changelog

Versions follow [semantic versioning](https://semver.org/). The version in
`manifest.json` is what HACS installs, and each release tag must match it.

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
