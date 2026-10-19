-- Create a database named spare_parts_assessment and connect to it before running this script.

CREATE TABLE suppliers (
    supplier_id INT PRIMARY KEY,
    supplier_name VARCHAR(100),
    city VARCHAR(50)
);

CREATE TABLE parts (
    part_id INT PRIMARY KEY,
    part_name VARCHAR(100),
    category VARCHAR(50),
    unit_price DECIMAL(10,2),
    stock_qty INT
);

CREATE TABLE purchase_orders (
    po_id INT PRIMARY KEY,
    supplier_id INT REFERENCES suppliers(supplier_id),
    order_date DATE,
    status VARCHAR(30)
);

CREATE TABLE purchase_order_items (
    po_item_id INT PRIMARY KEY,
    po_id INT REFERENCES purchase_orders(po_id),
    part_id INT REFERENCES parts(part_id),
    quantity INT
);

INSERT INTO suppliers VALUES
(1,'Axis Components','Rajkot'),
(2,'Prime Industrial','Pune'),
(3,'Nova Engineering','Coimbatore'),
(4,'Delta Supply Works','Bhubaneswar'),
(5,'Mektron Systems','Nashik'),
(6,'Cobalt Traders','Surat');

INSERT INTO parts VALUES
(101,'Bearing Set','Mechanical',1250,38),
(102,'Control Relay','Electrical',850,60),
(103,'Hydraulic Seal','Mechanical',420,95),
(104,'Temperature Sensor','Electronics',1850,24),
(105,'Drive Belt','Mechanical',760,42),
(106,'PLC Module','Electronics',5400,10),
(107,'Fuse Pack','Electrical',290,120);

INSERT INTO purchase_orders VALUES
(1001,1,'2026-10-01','Received'),
(1002,2,'2026-10-02','Pending'),
(1003,3,'2026-10-03','Received'),
(1004,1,'2026-10-05','Pending'),
(1005,5,'2026-10-06','Cancelled');

INSERT INTO purchase_order_items VALUES
(1,1001,101,10),
(2,1001,103,20),
(3,1002,102,15),
(4,1002,104,6),
(5,1003,105,12),
(6,1003,107,30),
(7,1004,106,2),
(8,1005,103,10);
