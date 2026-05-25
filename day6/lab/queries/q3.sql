SELECT customer_id, merchant_id, SUM(amount)
FROM FACT_TRANSACTIONS
WHERE STATUS = 'COMPLETED'
GROUP BY merchant_id;
