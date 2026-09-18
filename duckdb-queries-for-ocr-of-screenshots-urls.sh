echo "winners having low scores:"

duckdb -c "
WITH ranked AS (
  SELECT 
    image_index,
    image_file,
    score,
    candidate_text,
    rank,
    score - LEAD(score) OVER (PARTITION BY image_file ORDER BY rank) AS diff,
    MAX(CASE WHEN rank = 2 THEN candidate_text END) OVER (PARTITION BY image_file) AS loser_text
  FROM 'url_scores_summary.csv'
)
SELECT 
  image_index,
  score AS winner_score, 
  diff AS score_diff,
  candidate_text AS winner_text,
  loser_text
FROM ranked
WHERE rank = 1 AND score <= 15
ORDER BY score ASC, diff ASC;
"

echo "biggest score differences between winners and losers:"

duckdb -c "
WITH ranked AS (
  SELECT 
    image_index,
    image_file,
    score,
    candidate_text,
    rank,
    score - LEAD(score) OVER (PARTITION BY image_file ORDER BY rank) AS diff,
    MAX(CASE WHEN rank = 2 THEN candidate_text END) OVER (PARTITION BY image_file) AS loser_text
  FROM 'url_scores_summary.csv'
)
SELECT 
  image_index,
  diff, 
  score AS winner_score, 
  candidate_text AS winner_text,
  loser_text
FROM ranked
WHERE rank = 1 AND diff IS NOT NULL
ORDER BY diff DESC
LIMIT 10;
"
