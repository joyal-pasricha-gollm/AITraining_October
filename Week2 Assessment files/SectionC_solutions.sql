-- Section C - PostgreSQL / SQL
-- Create a database named spare_parts_assessment. Connect to it and run spare_parts_setup.sql.
-- Complete the following SQL tasks.
-- C1. Display all parts belonging to the Mechanical category.
select *
from parts 
where category = 'Mechanical';

-- C2. Display parts with unit_price above 1000, ordered from highest price to lowest.
select * from parts where unit_price > 1000 order by unit_price desc;

-- C3. Find the average unit_price for each category.
select category, avg(unit_price) as average_unit_price from parts
group by category
order by category;

-- C4. Find the total stock quantity for each category.
select category, sum(stock_qty) as total_stock_quantity from parts
group by category
order by category;


-- C5. Display every purchase order with supplier_name, order_date and status using a JOIN.
select po.po_id, s.supplier_name,po.order_date,po.status from purchase_orders as po
join suppliers as s
on po.supplier_id = s.supplier_id
order by po.po_id;

-- C6. Join purchase_orders, purchase_order_items and parts to display po_id, part_name, quantity and unit_price.
select po.po_id, p.part_name, poi.quantity, p.unit_price from purchase_orders as po
join purchase_order_items as poi
on po.po_id = poi.po_id
join parts as p
on poi.part_id = p.part_id
order by po.po_id, p.part_id;

-- C7. Extend the previous query to calculate line_total = quantity × unit_price.
select po.po_id, p.part_name, poi.quantity, p.unit_price, poi.quantity * p.unit_price as line_total
from purchase_orders as po
join purchase_order_items as poi
on po.po_id = poi.po_id
join  parts as p
on poi.part_id = p.part_id
order by po.po_id, p.part_id;


-- C8. Use a LEFT JOIN to display all suppliers, including suppliers that have never received a purchase order.
select s.supplier_id, s.supplier_name, s.city, po.po_id, po.order_date, po.status
from suppliers as s 
left join purchase_orders as po
on s.supplier_id = po.supplier_id
order by s.supplier_id, po.po_id;

-- C9. Display only suppliers that have no purchase orders.
select s.supplier_id, s.supplier_name, s.city
from suppliers as s
left join purchase_orders as po
on s.supplier_id = po.supplier_id
where po.po_id is null
order by s.supplier_id;

-- C10. Create a view named purchase_order_summary showing po_id, supplier_name, part_name, quantity,
-- unit_price, line_total and status. Query the view for Pending orders.

create or replace view purchase_order_summary as 
select po.po_id, s.supplier_name, p.part_name, poi.quantity, p.unit_price, poi.quantity * p.unit_price as line_total, po.status
from purchase_orders as po
join suppliers as s
on po.supplier_id = s.supplier_id
join purchase_order_items as poi
on po.po_id = poi.po_id
join parts as p
on poi.part_id = p.part_id;
--query view for pending orders
select * from purchase_order_summary
where status = 'Pending'
order by poi.po_id = po.part_id;

-- C11. Create a function calculate_part_discount(amount): if amount >= 2000 return 10% of amount, otherwise return 0. Use it with the parts table.
create or replace function calculate_part_discount(amount NUMERIC)
returns NUMERIC
LANGUAGE SQL
IMMUTABLE
AS $$
select case 
when amount >=2000 then amount * 0.10
else 0
end;
$$;

select part_id, part_name, unit_price, calculate_part_discount(unit_price) as discount
from parts
order by part_id;


-- C12. Create a function final_part_price(amount) that returns amount minus calculate_part_discount(amount). Use it in a SELECT query.
create or replace function final_part_price(amount NUMERIC)
returns NUMERIC
LANGUAGE SQL
IMMUTABLE
AS $$
select amount - calculate_part_discount(amount);
$$;
select part_id, part_name, unit_price, calculate_part_discount(unit_price) as discount, 
final_part_price(unit_price) as final_price
from parts
order by part_id;

-- C13. Create a stored procedure with parameters named update_po_status that accepts po_id and new_status and updates the matching purchase order. Call it once and verify the result.
create or replace procedure update_po_status(p_po_id int, p_new_status varchar(30))
LANGUAGE plpgsql
as $$
begin
update purchase_orders
set status = p_new_status
where po_id = p_po_id;
end;
$$;
calling procedure
call update_po_status(1005, 'Received')
select * from purchase_orders where po_id = 1005;

-- C14. Create a stored procedure without parameters named mark_old_pending_orders that changes Pending
-- orders dated before 2026-10-04 to Received. Run it and verify the results.
create or replace procedure mark_old_pending_orders()
LANGUAGE plpgsql
as $$
begin
update purchase_orders
set status = 'Received'
where status = 'Pending' and order_date < date '2026-10-04';
end;
$$;
-- calling procedure
call mark_old_pending_orders();
select po_id, supplier_id, order_date, status from purchase_orders order by po_id;

-- C15. Normalization question: Suppose supplier_name, supplier_city, part_name, part_category, po_id and
-- quantity were all stored repeatedly in one large table. Identify at least two repeated facts and suggest how you
-- would separate the data into tables.

-- -- Answer :
-- Repeated observations:
-- 1. supplier_name and supplier_city would be repeated every time the same supplier appears in another purchase order.
-- 2. part_name and part_category would be repeated every time the same part appears in another purchase order. 
-- A normlaised design would separte the data into:
-- SUPPLIERS: supplier_id(primnary key-pk), supplier name, city
-- PARTS: part_id(PK), part_name, category, unit_price, stock_qty
-- PURCHASE ORDERS: po_id(PK),  supplier_id(FK), order_date, status
-- PURCHASE_ORDER_ITEMS: po_itemsid(PK), po_id(FK), part_id(FK), quantity
-- thisbreduces repeated data and prevents insert, update and delete anomolies.