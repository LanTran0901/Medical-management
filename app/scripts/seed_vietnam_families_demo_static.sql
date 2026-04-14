-- Static demo seed (lightweight, no heavy loops)
-- Run:
-- psql "$POSTGRES_SYNC_URL" -f app/scripts/seed_vietnam_families_demo_static.sql

BEGIN;

TRUNCATE TABLE
  schedule_logs, schedules, growth_records, vaccine_history, medical_records,
  medicine_inventory, activity_logs, family_memberships, health_details, profiles,
  families, refresh_tokens, user_devices, users, diseases, drugs, vaccines
RESTART IDENTITY CASCADE;

-- users (12)
INSERT INTO users (id, email, password_hash, google_id, status, created_at, updated_at, deleted_at) VALUES
('11111111-1111-1111-1111-111111111001','an.nguyen@demo.vn','hash1',NULL,'active',now(),now(),NULL),
('11111111-1111-1111-1111-111111111002','binh.tran@demo.vn','hash2',NULL,'active',now(),now(),NULL),
('11111111-1111-1111-1111-111111111003','chi.le@demo.vn','hash3',NULL,'active',now(),now(),NULL),
('11111111-1111-1111-1111-111111111004','dung.pham@demo.vn','hash4',NULL,'active',now(),now(),NULL),
('11111111-1111-1111-1111-111111111005','ha.vo@demo.vn','hash5',NULL,'active',now(),now(),NULL),
('11111111-1111-1111-1111-111111111006','linh.hoang@demo.vn','hash6',NULL,'active',now(),now(),NULL),
('11111111-1111-1111-1111-111111111007','mai.bui@demo.vn','hash7',NULL,'active',now(),now(),NULL),
('11111111-1111-1111-1111-111111111008','nam.do@demo.vn','hash8',NULL,'active',now(),now(),NULL),
('11111111-1111-1111-1111-111111111009','ngoc.dang@demo.vn','hash9',NULL,'active',now(),now(),NULL),
('11111111-1111-1111-1111-111111111010','phuc.huynh@demo.vn','hash10',NULL,'active',now(),now(),NULL),
('11111111-1111-1111-1111-111111111011','thao.le@demo.vn','hash11',NULL,'active',now(),now(),NULL),
('11111111-1111-1111-1111-111111111012','tuan.nguyen@demo.vn','hash12',NULL,'active',now(),now(),NULL);

-- user_devices + refresh_tokens
INSERT INTO user_devices (id, user_id, fcm_token, device_name, platform, last_active) VALUES
('dev-001','11111111-1111-1111-1111-111111111001','fcm001','iPhone 14','ios',now()),
('dev-002','11111111-1111-1111-1111-111111111002','fcm002','Samsung A54','android',now()),
('dev-003','11111111-1111-1111-1111-111111111003','fcm003','iPhone 13','ios',now()),
('dev-004','11111111-1111-1111-1111-111111111004','fcm004','Xiaomi Note','android',now()),
('dev-005','11111111-1111-1111-1111-111111111005','fcm005','iPhone 12','ios',now()),
('dev-006','11111111-1111-1111-1111-111111111006','fcm006','Samsung S22','android',now()),
('dev-007','11111111-1111-1111-1111-111111111007','fcm007','iPad Air','ios',now()),
('dev-008','11111111-1111-1111-1111-111111111008','fcm008','Oppo Reno','android',now()),
('dev-009','11111111-1111-1111-1111-111111111009','fcm009','Pixel 8','android',now()),
('dev-010','11111111-1111-1111-1111-111111111010','fcm010','iPhone 15','ios',now()),
('dev-011','11111111-1111-1111-1111-111111111011','fcm011','Vivo Y36','android',now()),
('dev-012','11111111-1111-1111-1111-111111111012','fcm012','iPhone 11','ios',now());

INSERT INTO refresh_tokens (id, user_id, device_id, token_hash, expires_at, status) VALUES
('22222222-2222-2222-2222-222222222001','11111111-1111-1111-1111-111111111001','dev-001','tok001',now()+interval '30 days','ACTIVE'),
('22222222-2222-2222-2222-222222222002','11111111-1111-1111-1111-111111111002','dev-002','tok002',now()+interval '30 days','ACTIVE'),
('22222222-2222-2222-2222-222222222003','11111111-1111-1111-1111-111111111003','dev-003','tok003',now()+interval '30 days','ACTIVE'),
('22222222-2222-2222-2222-222222222004','11111111-1111-1111-1111-111111111004','dev-004','tok004',now()+interval '30 days','ACTIVE'),
('22222222-2222-2222-2222-222222222005','11111111-1111-1111-1111-111111111005','dev-005','tok005',now()+interval '30 days','ACTIVE'),
('22222222-2222-2222-2222-222222222006','11111111-1111-1111-1111-111111111006','dev-006','tok006',now()+interval '30 days','ACTIVE'),
('22222222-2222-2222-2222-222222222007','11111111-1111-1111-1111-111111111007','dev-007','tok007',now()+interval '30 days','ACTIVE'),
('22222222-2222-2222-2222-222222222008','11111111-1111-1111-1111-111111111008','dev-008','tok008',now()+interval '30 days','ACTIVE'),
('22222222-2222-2222-2222-222222222009','11111111-1111-1111-1111-111111111009','dev-009','tok009',now()+interval '30 days','ACTIVE'),
('22222222-2222-2222-2222-222222222010','11111111-1111-1111-1111-111111111010','dev-010','tok010',now()+interval '30 days','ACTIVE'),
('22222222-2222-2222-2222-222222222011','11111111-1111-1111-1111-111111111011','dev-011','tok011',now()+interval '30 days','ACTIVE'),
('22222222-2222-2222-2222-222222222012','11111111-1111-1111-1111-111111111012','dev-012','tok012',now()+interval '30 days','ACTIVE');

-- families (3)
INSERT INTO families (id, family_name, invite_code, created_at) VALUES
('33333333-3333-3333-3333-333333333001','Gia đình An Khang','VNDEMO001',now()),
('33333333-3333-3333-3333-333333333002','Gia đình Hạnh Phúc','VNDEMO002',now()),
('33333333-3333-3333-3333-333333333003','Gia đình Sum Vầy','VNDEMO003',now());

-- profiles (12 linked + 3 virtual)
INSERT INTO profiles (id, owner_user_id, linked_user_id, full_name, dob, gender, height_cm, weight_kg, address, avatar_url, status, created_at, updated_at, deleted_at) VALUES
('44444444-4444-4444-4444-444444444001','11111111-1111-1111-1111-111111111001','11111111-1111-1111-1111-111111111001','Nguyễn An','1988-01-12','male',170,67,'Q.1, TP.HCM','https://demo.vn/a1.png','active',now(),now(),NULL),
('44444444-4444-4444-4444-444444444002','11111111-1111-1111-1111-111111111002','11111111-1111-1111-1111-111111111002','Trần Bình','1990-03-20','male',172,70,'Q.7, TP.HCM','https://demo.vn/a2.png','active',now(),now(),NULL),
('44444444-4444-4444-4444-444444444003','11111111-1111-1111-1111-111111111003','11111111-1111-1111-1111-111111111003','Lê Chi','1992-07-18','female',160,52,'Thủ Đức, TP.HCM','https://demo.vn/a3.png','active',now(),now(),NULL),
('44444444-4444-4444-4444-444444444004','11111111-1111-1111-1111-111111111004','11111111-1111-1111-1111-111111111004','Phạm Dũng','1987-11-11','male',168,65,'Q.3, TP.HCM','https://demo.vn/a4.png','active',now(),now(),NULL),
('44444444-4444-4444-4444-444444444005','11111111-1111-1111-1111-111111111005','11111111-1111-1111-1111-111111111005','Võ Hà','1991-05-05','female',158,50,'Hà Nội','https://demo.vn/b1.png','active',now(),now(),NULL),
('44444444-4444-4444-4444-444444444006','11111111-1111-1111-1111-111111111006','11111111-1111-1111-1111-111111111006','Hoàng Linh','1993-08-09','female',162,55,'Hà Nội','https://demo.vn/b2.png','active',now(),now(),NULL),
('44444444-4444-4444-4444-444444444007','11111111-1111-1111-1111-111111111007','11111111-1111-1111-1111-111111111007','Bùi Mai','1989-10-01','female',159,51,'Đà Nẵng','https://demo.vn/b3.png','active',now(),now(),NULL),
('44444444-4444-4444-4444-444444444008','11111111-1111-1111-1111-111111111008','11111111-1111-1111-1111-111111111008','Đỗ Nam','1986-04-14','male',174,72,'Đà Nẵng','https://demo.vn/b4.png','active',now(),now(),NULL),
('44444444-4444-4444-4444-444444444009','11111111-1111-1111-1111-111111111009','11111111-1111-1111-1111-111111111009','Đặng Ngọc','1995-02-17','female',161,54,'Hải Phòng','https://demo.vn/c1.png','active',now(),now(),NULL),
('44444444-4444-4444-4444-444444444010','11111111-1111-1111-1111-111111111010','11111111-1111-1111-1111-111111111010','Huỳnh Phúc','1988-12-30','male',171,69,'Cần Thơ','https://demo.vn/c2.png','active',now(),now(),NULL),
('44444444-4444-4444-4444-444444444011','11111111-1111-1111-1111-111111111011','11111111-1111-1111-1111-111111111011','Lê Thảo','1994-06-23','female',157,49,'Huế','https://demo.vn/c3.png','active',now(),now(),NULL),
('44444444-4444-4444-4444-444444444012','11111111-1111-1111-1111-111111111012','11111111-1111-1111-1111-111111111012','Nguyễn Tuấn','1985-09-29','male',175,74,'Nha Trang','https://demo.vn/c4.png','active',now(),now(),NULL),
('44444444-4444-4444-4444-444444444101','11111111-1111-1111-1111-111111111001',NULL,'Bé Mít A','2018-01-01','female',112,20,'Q.1, TP.HCM','https://demo.vn/v1.png','virtual',now(),now(),NULL),
('44444444-4444-4444-4444-444444444102','11111111-1111-1111-1111-111111111005',NULL,'Bé Mít B','2019-02-02','male',108,18,'Hà Nội','https://demo.vn/v2.png','virtual',now(),now(),NULL),
('44444444-4444-4444-4444-444444444103','11111111-1111-1111-1111-111111111009',NULL,'Bé Mít C','2020-03-03','female',102,16,'Hải Phòng','https://demo.vn/v3.png','virtual',now(),now(),NULL);

INSERT INTO health_details (id, profile_id, blood_type, chronic_diseases, allergies, emergency_contacts, notes, updated_at)
SELECT
  gen_random_uuid(),
  p.id,
  'O_POS'::blood_type_enum,
  ARRAY['Không'],
  ARRAY['Không'],
  '[{"name":"Liên hệ khẩn cấp","phone":"0900000000","relationship":"Người nhà"}]'::jsonb,
  'Dữ liệu demo',
  now()
FROM profiles p;

INSERT INTO family_memberships (id, family_id, profile_id, role, added_by, created_at) VALUES
-- family 1
('55555555-5555-5555-5555-555555555001','33333333-3333-3333-3333-333333333001','44444444-4444-4444-4444-444444444001','OWNER','11111111-1111-1111-1111-111111111001',now()),
('55555555-5555-5555-5555-555555555002','33333333-3333-3333-3333-333333333001','44444444-4444-4444-4444-444444444002','ADMIN','11111111-1111-1111-1111-111111111001',now()),
('55555555-5555-5555-5555-555555555003','33333333-3333-3333-3333-333333333001','44444444-4444-4444-4444-444444444003','MEMBER','11111111-1111-1111-1111-111111111001',now()),
('55555555-5555-5555-5555-555555555004','33333333-3333-3333-3333-333333333001','44444444-4444-4444-4444-444444444004','MEMBER','11111111-1111-1111-1111-111111111001',now()),
('55555555-5555-5555-5555-555555555005','33333333-3333-3333-3333-333333333001','44444444-4444-4444-4444-444444444101','MEMBER','11111111-1111-1111-1111-111111111001',now()),
-- family 2
('55555555-5555-5555-5555-555555555006','33333333-3333-3333-3333-333333333002','44444444-4444-4444-4444-444444444005','OWNER','11111111-1111-1111-1111-111111111005',now()),
('55555555-5555-5555-5555-555555555007','33333333-3333-3333-3333-333333333002','44444444-4444-4444-4444-444444444006','ADMIN','11111111-1111-1111-1111-111111111005',now()),
('55555555-5555-5555-5555-555555555008','33333333-3333-3333-3333-333333333002','44444444-4444-4444-4444-444444444007','MEMBER','11111111-1111-1111-1111-111111111005',now()),
('55555555-5555-5555-5555-555555555009','33333333-3333-3333-3333-333333333002','44444444-4444-4444-4444-444444444008','MEMBER','11111111-1111-1111-1111-111111111005',now()),
('55555555-5555-5555-5555-555555555010','33333333-3333-3333-3333-333333333002','44444444-4444-4444-4444-444444444102','MEMBER','11111111-1111-1111-1111-111111111005',now()),
-- family 3
('55555555-5555-5555-5555-555555555011','33333333-3333-3333-3333-333333333003','44444444-4444-4444-4444-444444444009','OWNER','11111111-1111-1111-1111-111111111009',now()),
('55555555-5555-5555-5555-555555555012','33333333-3333-3333-3333-333333333003','44444444-4444-4444-4444-444444444010','ADMIN','11111111-1111-1111-1111-111111111009',now()),
('55555555-5555-5555-5555-555555555013','33333333-3333-3333-3333-333333333003','44444444-4444-4444-4444-444444444011','MEMBER','11111111-1111-1111-1111-111111111009',now()),
('55555555-5555-5555-5555-555555555014','33333333-3333-3333-3333-333333333003','44444444-4444-4444-4444-444444444012','MEMBER','11111111-1111-1111-1111-111111111009',now()),
('55555555-5555-5555-5555-555555555015','33333333-3333-3333-3333-333333333003','44444444-4444-4444-4444-444444444103','MEMBER','11111111-1111-1111-1111-111111111009',now());

-- family_medicine_inventory
INSERT INTO family_medicine_inventory (id, family_id, created_by_user_id, medicine_name, expiry_date, quantity_stock, unit, min_stock_alert, note) VALUES
('66666666-6666-6666-6666-666666666001','33333333-3333-3333-3333-333333333001','11111111-1111-1111-1111-111111111001','Paracetamol 500mg',current_date+180,20,'viên',3,'Uống sau ăn'),
('66666666-6666-6666-6666-666666666002','33333333-3333-3333-3333-333333333001','11111111-1111-1111-1111-111111111001','Vitamin C',current_date+250,10,'ống',2,'Sáng 1 viên'),
('66666666-6666-6666-6666-666666666003','33333333-3333-3333-3333-333333333001','11111111-1111-1111-1111-111111111001','ORS',current_date+300,15,'gói',3,'Bù nước'),
('66666666-6666-6666-6666-666666666004','33333333-3333-3333-3333-333333333002','11111111-1111-1111-1111-111111111005','Ibuprofen 400mg',current_date+200,18,'viên',3,'Sau ăn'),
('66666666-6666-6666-6666-666666666005','33333333-3333-3333-3333-333333333002','11111111-1111-1111-1111-111111111005','Amoxicillin',current_date+120,30,'viên',5,'Theo toa bác sĩ'),
('66666666-6666-6666-6666-666666666006','33333333-3333-3333-3333-333333333002','11111111-1111-1111-1111-111111111005','Nước muối sinh lý',current_date+240,8,'chai',2,'Nhỏ mũi'),
('66666666-6666-6666-6666-666666666007','33333333-3333-3333-3333-333333333003','11111111-1111-1111-1111-111111111009','Omega-3',current_date+365,25,'viên',5,'Mỗi ngày 1 viên'),
('66666666-6666-6666-6666-666666666008','33333333-3333-3333-3333-333333333003','11111111-1111-1111-1111-111111111009','Canxi Nano',current_date+320,40,'viên',6,'Sau ăn sáng'),
('66666666-6666-6666-6666-666666666009','33333333-3333-3333-3333-333333333003','11111111-1111-1111-1111-111111111009','Siro ho',current_date+150,6,'chai',1,'5ml/lần');

-- medical_records, vaccine_history, schedules, logs, growth, activity (nhẹ)
INSERT INTO medical_records (id, profile_id, created_by, diagnosis_name, diagnosis_slug, doctor_name, hospital_name, visit_date, attachment_urls, created_at)
SELECT gen_random_uuid(), p.id, p.owner_user_id, 'Cảm cúm mùa', 'cam-cum-mua', 'BS. Nguyễn Văn A', 'BV Bạch Mai', current_date-30, jsonb_build_object('files',jsonb_build_array('https://demo.vn/r.pdf')), now()
FROM profiles p;

INSERT INTO vaccine_history (id, profile_id, vaccine_name, dose_number, vaccinated_date, next_due_date)
SELECT gen_random_uuid(), p.id, 'Cúm mùa', 1, current_date-120, current_date+240
FROM profiles p;

INSERT INTO schedules (id, profile_id, medicine_id, title, category, remind_time, dosage_per_time, rrule, status)
SELECT gen_random_uuid(), p.id, m.id, 'Nhắc uống thuốc', 'MEDICINE'::schedule_category, '08:00:00', 1, 'FREQ=DAILY', 'ACTIVE'::schedule_status
FROM profiles p
JOIN LATERAL (SELECT id FROM medicine_inventory ORDER BY id LIMIT 1) m ON TRUE;

INSERT INTO schedule_logs (id, schedule_id, status, action_by, action_time)
SELECT gen_random_uuid(), s.id, 'DONE', p.owner_user_id, now()-interval '1 day'
FROM schedules s
JOIN profiles p ON p.id=s.profile_id;

INSERT INTO growth_records (id, profile_id, height_cm, weight_kg, recorded_at)
SELECT gen_random_uuid(), p.id, 120, 25, current_date-90
FROM profiles p;

INSERT INTO activity_logs (id, family_id, user_id, action_desc, created_at) VALUES
('77777777-7777-7777-7777-777777777001','33333333-3333-3333-3333-333333333001','11111111-1111-1111-1111-111111111001','Đã tạo hồ sơ thành viên mới',now()),
('77777777-7777-7777-7777-777777777002','33333333-3333-3333-3333-333333333001','11111111-1111-1111-1111-111111111002','Đã cập nhật thông tin sức khỏe',now()),
('77777777-7777-7777-7777-777777777003','33333333-3333-3333-3333-333333333002','11111111-1111-1111-1111-111111111005','Đã thêm lịch nhắc uống thuốc',now()),
('77777777-7777-7777-7777-777777777004','33333333-3333-3333-3333-333333333002','11111111-1111-1111-1111-111111111006','Đã bổ sung thuốc trong tủ gia đình',now()),
('77777777-7777-7777-7777-777777777005','33333333-3333-3333-3333-333333333003','11111111-1111-1111-1111-111111111009','Đã ghi nhận mũi tiêm mới',now()),
('77777777-7777-7777-7777-777777777006','33333333-3333-3333-3333-333333333003','11111111-1111-1111-1111-111111111010','Đã cập nhật thông tin sức khỏe',now());

-- dictionary sample
INSERT INTO diseases (source_index,title,aliases,summary,content,source_file) VALUES
(1,'Bệnh demo 1','["BenhDemo1"]','Demo','{"overview":"Mo ta benh 1","lang":"vi"}','seed_static.sql'),
(2,'Bệnh demo 2','["BenhDemo2"]','Demo','{"overview":"Mo ta benh 2","lang":"vi"}','seed_static.sql'),
(3,'Bệnh demo 3','["BenhDemo3"]','Demo','{"overview":"Mo ta benh 3","lang":"vi"}','seed_static.sql');

INSERT INTO drugs (source_index,title,aliases,summary,content,source_file) VALUES
(1,'Thuốc demo 1','["ThuocDemo1"]','Demo','{"indications":"Chi dinh 1","lang":"vi"}','seed_static.sql'),
(2,'Thuốc demo 2','["ThuocDemo2"]','Demo','{"indications":"Chi dinh 2","lang":"vi"}','seed_static.sql'),
(3,'Thuốc demo 3','["ThuocDemo3"]','Demo','{"indications":"Chi dinh 3","lang":"vi"}','seed_static.sql');

INSERT INTO vaccines (source_index,title,aliases,summary,content,source_file) VALUES
(1,'Vaccine demo 1','["VaccineDemo1"]','Demo','{"prevents_disease":"Ngoa benh 1","lang":"vi"}','seed_static.sql'),
(2,'Vaccine demo 2','["VaccineDemo2"]','Demo','{"prevents_disease":"Ngoa benh 2","lang":"vi"}','seed_static.sql'),
(3,'Vaccine demo 3','["VaccineDemo3"]','Demo','{"prevents_disease":"Ngoa benh 3","lang":"vi"}','seed_static.sql');

COMMIT;
