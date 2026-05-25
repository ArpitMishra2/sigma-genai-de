SELECT customer_id, SUM(amount)
FROM transactions
GROUP BY merchant_id;
