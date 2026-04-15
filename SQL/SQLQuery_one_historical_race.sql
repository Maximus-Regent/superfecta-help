SELECT TOP (8)
    s.registration_number,
    s.program_number,
    r.track_id,
    r.race_date,
    r.race_number,
    s.odds,
    s.position_at_start,
    s.official_position,
    s.scratch_indicator,
    e.winning_numbers,
    e.number_of_tickets_bet,
    e.total_pool,
    e.payoff_amount,
    r.distance_id,
    r.surface,
    r.course_type,
    r.purse_usa,
    r.post_time,
    r.track_condition,
    r.number_of_runners,
    s.post_position
FROM dbo.start          AS s
JOIN dbo.race           AS r
  ON s.track_id        = r.track_id
 AND s.race_date       = r.race_date
 AND s.race_number     = r.race_number
 AND s.country         = r.country
JOIN dbo.exotic_payoff AS e
  ON r.track_id        = e.track_id
 AND r.race_date       = e.race_date
 AND r.race_number     = e.race_number
 AND r.country         = e.country
WHERE
    -- date window, excluding all of 2021
    --r.race_date BETWEEN '2010-06-01' AND '2025-06-01'
    --AND YEAR(r.race_date) <> 2021
   r.track_id       = 'SAR'
    AND r.race_date  = '2025-07-05'
    AND r.race_number = 5 

    -- only these specific tracks
    AND r.track_id IN (
        'CD ', 'GP ', 'SA ',
        'AQU', 'BAQ', 'BEL',
        'SAR', 'KEE', 'DMR',
        'MTH', 'OP'
    )

    -- race has at least 6 runners
    AND r.number_of_runners >= 6

    -- only non-scratched starters
    AND s.scratch_indicator = 'N'

    -- only “S” exotic payoffs with real pools and payoffs
    AND e.wager_type    = 'S'
    AND e.total_pool    >  0
    AND e.payoff_amount >  0
    AND e.number_of_tickets_bet > 0

ORDER BY
    r.race_date DESC,
    r.track_id,
    r.race_number;
