# Synthetic training input

seed.json contains deliberately fictional training records, identified by synthetic=true metadata. Country labels provide context; player/team identities, venue capacities, scorecards and career statistics are invented. Simplified six-player scorecards and generated run/ball distributions are not realistic match simulations.

The fixture has 12 players, 72 matches over 12 quarters, 192 innings and two career snapshot batches. Its fixed analysis date is 2026-10-01. Career totals are independent of the imported match history. The latest snapshot view chooses a snapshot rather than adding them.

Load only into an explicitly initialized sample database with the documented --seed-sample option. Live initialization rejects that flag. Individual SQL lessons will add targeted boundary fixtures rather than claiming this dataset alone verifies every analytical question.
