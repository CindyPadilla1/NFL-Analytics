-- ============================================================
--  NFL Analytics — MySQL Schema & Analytical Queries
--  Database: nfl_analytics
-- ============================================================

CREATE DATABASE IF NOT EXISTS nfl_analytics;
USE nfl_analytics;

-- ── Tables are created by ingest.py via to_sql ────────────────
-- This file documents schema + provides all analytical queries.

-- ============================================================
--  1. TEAM OFFENSIVE EFFICIENCY  (EPA per play, by season)
-- ============================================================
SELECT
    season,
    posteam                          AS team,
    COUNT(*)                         AS total_plays,
    ROUND(AVG(epa), 4)               AS epa_per_play,
    ROUND(SUM(CASE WHEN play_type='pass' THEN 1 ELSE 0 END)/COUNT(*), 3) AS pass_rate,
    ROUND(AVG(CASE WHEN play_type='pass' THEN epa END), 4) AS pass_epa,
    ROUND(AVG(CASE WHEN play_type='run'  THEN epa END), 4) AS run_epa
FROM plays
WHERE season_type = 'REG'
GROUP BY season, posteam
ORDER BY season DESC, epa_per_play DESC;


-- ============================================================
--  2. THIRD DOWN CONVERSION RATES  (by team + season)
-- ============================================================
SELECT
    season,
    posteam                              AS team,
    COUNT(*)                             AS third_down_attempts,
    SUM(third_down_converted)            AS conversions,
    ROUND(AVG(third_down_converted)*100, 1) AS conversion_pct,
    ROUND(AVG(ydstogo), 1)              AS avg_distance
FROM plays
WHERE down = 3
GROUP BY season, posteam
ORDER BY season DESC, conversion_pct DESC;


-- ============================================================
--  3. RED ZONE SCORING EFFICIENCY
-- ============================================================
SELECT
    season,
    posteam                                   AS team,
    COUNT(*)                                  AS red_zone_plays,
    SUM(touchdown)                            AS touchdowns,
    ROUND(SUM(touchdown)/COUNT(*)*100, 1)    AS td_rate_pct,
    ROUND(AVG(epa), 4)                        AS avg_epa
FROM plays
WHERE red_zone = 1
GROUP BY season, posteam
ORDER BY season DESC, td_rate_pct DESC;


-- ============================================================
--  4. RUN/PASS TENDENCY BY DOWN & DISTANCE
-- ============================================================
SELECT
    down,
    CASE
        WHEN ydstogo <= 3  THEN 'Short (1-3)'
        WHEN ydstogo <= 7  THEN 'Medium (4-7)'
        WHEN ydstogo <= 10 THEN 'Standard (8-10)'
        ELSE 'Long (11+)'
        END                                                    AS distance_bucket,
    COUNT(*)                                               AS plays,
    ROUND(AVG(CASE WHEN play_type='pass' THEN 1 ELSE 0 END)*100, 1) AS pass_rate_pct
FROM plays
GROUP BY down, distance_bucket
ORDER BY down, MIN(ydstogo);


-- ============================================================
--  5. BEARS-SPECIFIC ANALYSIS  (CHI)
-- ============================================================
SELECT
    season,
    play_type,
    COUNT(*)                     AS plays,
    ROUND(AVG(epa), 4)           AS epa_per_play,
    ROUND(AVG(yards_gained), 2)  AS avg_yards,
    SUM(touchdown)               AS touchdowns
FROM plays
WHERE posteam = 'CHI'
GROUP BY season, play_type
ORDER BY season DESC, play_type;


-- ============================================================
--  6. BEARS vs NFC NORTH RIVALS  (EPA comparison)
-- ============================================================
SELECT
    season,
    posteam                       AS team,
    COUNT(*)                      AS plays,
    ROUND(AVG(epa), 4)            AS epa_per_play,
    ROUND(AVG(CASE WHEN play_type='pass' THEN epa END), 4) AS pass_epa,
    ROUND(AVG(CASE WHEN play_type='run'  THEN epa END), 4) AS run_epa,
    ROUND(AVG(CASE WHEN play_type='pass' THEN 1.0 ELSE 0 END)*100, 1) AS pass_rate_pct
FROM plays
WHERE posteam IN ('CHI', 'GB', 'MIN', 'DET')
GROUP BY season, posteam
ORDER BY season DESC, epa_per_play DESC;


-- ============================================================
--  7. PLAYER EFFICIENCY  (Top passers by EPA)
-- ============================================================
SELECT
    season,
    passer_player_name            AS passer,
    COUNT(*)                      AS dropbacks,
    ROUND(AVG(epa), 4)            AS epa_per_dropback,
    ROUND(AVG(air_yards), 1)      AS avg_air_yards,
    SUM(touchdown)                AS tds,
    SUM(interception)             AS ints
FROM plays
WHERE play_type = 'pass'
  AND qb_scramble = 0
  AND passer_player_name IS NOT NULL
GROUP BY season, passer_player_name
HAVING dropbacks >= 100
ORDER BY season DESC, epa_per_dropback DESC
    LIMIT 30;


-- ============================================================
--  8. GAME SITUATION  (Score diff buckets — run/pass split)
-- ============================================================
SELECT
    CASE
        WHEN score_differential <= -14 THEN 'Down 14+'
        WHEN score_differential <= -7  THEN 'Down 7-13'
        WHEN score_differential <= -1  THEN 'Down 1-6'
        WHEN score_differential = 0    THEN 'Tied'
        WHEN score_differential <= 6   THEN 'Up 1-6'
        WHEN score_differential <= 13  THEN 'Up 7-13'
        ELSE 'Up 14+'
        END                                                       AS game_situation,
    COUNT(*)                                                  AS plays,
    ROUND(AVG(CASE WHEN play_type='pass' THEN 1 ELSE 0 END)*100, 1) AS pass_rate_pct,
    ROUND(AVG(epa), 4)                                        AS avg_epa
FROM plays
GROUP BY game_situation
ORDER BY MIN(score_differential);