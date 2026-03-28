-- Vietnam demo seed (PostgreSQL)
-- Import:
--   psql "$POSTGRES_SYNC_URL" -f app/scripts/seed_vietnam_families_demo.sql

BEGIN;

-- 1) Clean demo data (safe for local/demo only)
TRUNCATE TABLE
  schedule_logs,
  schedules,
  growth_records,
  vaccine_history,
  medical_records,
  medicine_inventory,
  activity_logs,
  family_memberships,
  health_details,
  profiles,
  families,
  refresh_tokens,
  user_devices,
  users,
  diseases,
  drugs,
  vaccines
RESTART IDENTITY CASCADE;

-- 2) Core users / families / profiles / memberships / auth tables
DO $$
DECLARE
  f int;
  u int;
  fam_id uuid;
  usr_id uuid;
  owner_user_id uuid;
  prof_id uuid;
  role_text family_role;
BEGIN
  FOR f IN 1..12 LOOP
    fam_id := gen_random_uuid();

    INSERT INTO families (id, family_name, invite_code, created_at)
    VALUES (
      fam_id,
      format('Gia đình Việt %s', f),
      format('VN%02s%s', f, upper(substr(md5(random()::text), 1, 8))),
      now() - (f || ' days')::interval
    );

    owner_user_id := NULL;

    FOR u IN 1..6 LOOP
      usr_id := gen_random_uuid();

      INSERT INTO users (id, email, password_hash, google_id, status, created_at, updated_at, deleted_at)
      VALUES (
        usr_id,
        format('demo.f%s.u%s@vietnam.local', f, u),
        md5(format('demo-%s-%s', f, u)),
        NULL,
        'active',
        now() - ((f * 10 + u) || ' days')::interval,
        now(),
        NULL
      );

      INSERT INTO user_devices (id, user_id, fcm_token, device_name, platform, last_active)
      VALUES (
        format('device-f%02s-u%02s', f, u),
        usr_id,
        format('fcm_%s', substr(md5(random()::text), 1, 24)),
        CASE WHEN u % 2 = 0 THEN 'iPhone 14' ELSE 'Samsung A54' END,
        CASE WHEN u % 2 = 0 THEN 'ios' ELSE 'android' END,
        now() - (u || ' hours')::interval
      );

      INSERT INTO refresh_tokens (id, user_id, device_id, token_hash, expires_at, status)
      VALUES (
        gen_random_uuid(),
        usr_id,
        format('device-f%02s-u%02s', f, u),
        md5(format('%s-%s-%s', f, u, random())),
        now() + interval '30 days',
        'ACTIVE'
      );

      prof_id := gen_random_uuid();
      INSERT INTO profiles (
        id, owner_user_id, linked_user_id, full_name, dob, gender, height_cm, weight_kg,
        address, avatar_url, status, created_at, updated_at, deleted_at
      )
      VALUES (
        prof_id,
        usr_id,
        usr_id,
        format('Thành viên %s-%s', f, u),
        current_date - ((18 + (u * 3))::text || ' years')::interval,
        CASE WHEN u % 3 = 0 THEN 'male'::gender_type WHEN u % 3 = 1 THEN 'female'::gender_type ELSE 'other'::gender_type END,
        150 + (u * 2),
        45 + (u * 3),
        format('%s Nguyễn Huệ, TP. Hồ Chí Minh', 10 + u),
        format('https://demo.vn/avatar/f%s-u%s.png', f, u),
        'active',
        now(),
        now(),
        NULL
      );

      INSERT INTO health_details (
        id, profile_id, blood_type, chronic_diseases, allergies, emergency_contact, notes, updated_at
      )
      VALUES (
        gen_random_uuid(),
        prof_id,
        (ARRAY['A_POS','A_NEG','B_POS','B_NEG','O_POS','O_NEG','AB_POS','AB_NEG'])[(1 + (u % 8))]::blood_type_enum,
        ARRAY['Không'],
        ARRAY['Không'],
        format('09%08s', trunc(random() * 100000000)::int),
        'Hồ sơ sức khỏe demo gia đình Việt',
        now()
      );

      IF u = 1 THEN
        owner_user_id := usr_id;
        role_text := 'OWNER';
      ELSIF u = 2 THEN
        role_text := 'ADMIN';
      ELSE
        role_text := 'MEMBER';
      END IF;

      INSERT INTO family_memberships (id, family_id, profile_id, role, added_by, created_at)
      VALUES (gen_random_uuid(), fam_id, prof_id, role_text, owner_user_id, now());
    END LOOP;

    -- one virtual/child profile per family
    prof_id := gen_random_uuid();
    INSERT INTO profiles (
      id, owner_user_id, linked_user_id, full_name, dob, gender, height_cm, weight_kg,
      address, avatar_url, status, created_at, updated_at, deleted_at
    )
    VALUES (
      prof_id,
      owner_user_id,
      NULL,
      format('Bé %s', f),
      current_date - interval '7 years',
      'female'::gender_type,
      118,
      22,
      format('%s Lê Lợi, Hà Nội', 20 + f),
      format('https://demo.vn/avatar/be-%s.png', f),
      'virtual',
      now(),
      now(),
      NULL
    );

    INSERT INTO health_details (
      id, profile_id, blood_type, chronic_diseases, allergies, emergency_contact, notes, updated_at
    )
    VALUES (
      gen_random_uuid(),
      prof_id,
      'O_POS'::blood_type_enum,
      ARRAY['Không'],
      ARRAY['Không'],
      format('09%08s', trunc(random() * 100000000)::int),
      'Hồ sơ trẻ em demo',
      now()
    );

    INSERT INTO family_memberships (id, family_id, profile_id, role, added_by, created_at)
    VALUES (gen_random_uuid(), fam_id, prof_id, 'MEMBER', owner_user_id, now());
  END LOOP;
END $$;

-- 3) medicine_inventory (5 rows/family)
INSERT INTO medicine_inventory (
  id, family_id, medicine_name, medicine_type, expiry_date,
  quantity_stock, unit, min_stock_alert, instruction
)
SELECT
  gen_random_uuid(),
  f.id,
  (ARRAY['Paracetamol 500mg','Vitamin C','Amoxicillin','Ibuprofen 400mg','ORS'])[(g.i % 5) + 1],
  (ARRAY['Viên nén','Viên sủi','Kháng sinh','Viên nén','Bù điện giải'])[(g.i % 5) + 1],
  current_date + ((180 + g.i * 15) || ' days')::interval,
  (5 + g.i)::numeric(12,3),
  (ARRAY['viên','ống','viên','viên','gói'])[(g.i % 5) + 1],
  3::numeric(12,3),
  'Bảo quản nơi khô ráo, tránh ánh sáng.'
FROM families f
CROSS JOIN generate_series(1,5) AS g(i);

-- 4) medical_records (2 rows/profile)
INSERT INTO medical_records (
  id, profile_id, created_by, diagnosis_name, diagnosis_slug, doctor_name,
  hospital_name, visit_date, attachment_urls, created_at
)
SELECT
  gen_random_uuid(),
  p.id,
  p.owner_user_id,
  (ARRAY['Cảm cúm mùa','Viêm họng cấp','Viêm mũi dị ứng','Đau dạ dày','Sốt siêu vi'])[(g.i % 5) + 1],
  (ARRAY['cam-cum-mua','viem-hong-cap','viem-mui-di-ung','dau-da-day','sot-sieu-vi'])[(g.i % 5) + 1],
  (ARRAY['BS. Nguyễn Văn A','BS. Trần Thu B','BS. Lê Minh C'])[(g.i % 3) + 1],
  (ARRAY['BV Bạch Mai','BV Chợ Rẫy','BV Đà Nẵng'])[(g.i % 3) + 1],
  current_date - ((g.i * 60) || ' days')::interval,
  jsonb_build_object('files', jsonb_build_array(format('https://demo.vn/records/%s.pdf', gen_random_uuid()))),
  now()
FROM profiles p
CROSS JOIN generate_series(1,2) AS g(i);

-- 5) vaccine_history (2 rows/profile)
INSERT INTO vaccine_history (id, profile_id, vaccine_name, dose_number, vaccinated_date, next_due_date)
SELECT
  gen_random_uuid(),
  p.id,
  (ARRAY['Viêm gan B','MMR','Cúm mùa','COVID-19'])[(g.i % 4) + 1],
  g.i,
  current_date - ((g.i * 120) || ' days')::interval,
  current_date + ((g.i * 180) || ' days')::interval
FROM profiles p
CROSS JOIN generate_series(1,2) AS g(i);

-- 6) schedules (2 rows/profile)
INSERT INTO schedules (
  id, profile_id, medicine_id, title, category, remind_time,
  dosage_per_time, rrule, status
)
SELECT
  gen_random_uuid(),
  p.id,
  (
    SELECT m.id
    FROM medicine_inventory m
    ORDER BY random()
    LIMIT 1
  ),
  CASE WHEN g.i = 1 THEN 'Nhắc uống thuốc buổi sáng' ELSE 'Nhắc tái khám' END,
  CASE WHEN g.i = 1 THEN 'MEDICINE'::schedule_category ELSE 'CHECKUP'::schedule_category END,
  CASE WHEN g.i = 1 THEN '08:00:00'::time ELSE '19:00:00'::time END,
  1::numeric(12,3),
  'FREQ=DAILY',
  'ACTIVE'::schedule_status
FROM profiles p
CROSS JOIN generate_series(1,2) AS g(i);

-- 7) schedule_logs (1 row/schedule)
INSERT INTO schedule_logs (id, schedule_id, status, action_by, action_time)
SELECT
  gen_random_uuid(),
  s.id,
  (ARRAY['DONE','SKIPPED','LATE'])[(1 + (random() * 2)::int)],
  p.owner_user_id,
  now() - interval '1 day'
FROM schedules s
JOIN profiles p ON p.id = s.profile_id;

-- 8) growth_records (3 rows/profile)
INSERT INTO growth_records (id, profile_id, height_cm, weight_kg, recorded_at)
SELECT
  gen_random_uuid(),
  p.id,
  (120 + g.i * 1.5)::numeric(6,2),
  (25 + g.i * 0.8)::numeric(6,2),
  current_date - ((g.i * 90) || ' days')::interval
FROM profiles p
CROSS JOIN generate_series(1,3) AS g(i);

-- 9) activity_logs (8 rows/family)
INSERT INTO activity_logs (id, family_id, user_id, action_desc, created_at)
SELECT
  gen_random_uuid(),
  f.id,
  (
    SELECT p.linked_user_id
    FROM family_memberships fm
    JOIN profiles p ON p.id = fm.profile_id
    WHERE fm.family_id = f.id
      AND p.linked_user_id IS NOT NULL
    ORDER BY random()
    LIMIT 1
  ),
  (ARRAY[
    'Đã tạo hồ sơ thành viên mới',
    'Đã cập nhật thông tin sức khỏe',
    'Đã thêm lịch nhắc uống thuốc',
    'Đã bổ sung thuốc trong tủ gia đình',
    'Đã ghi nhận mũi tiêm mới'
  ])[(g.i % 5) + 1],
  now() - ((g.i * 2) || ' days')::interval
FROM families f
CROSS JOIN generate_series(1,8) AS g(i);

-- 10) dictionary tables (30 rows each)
INSERT INTO diseases (source_index, title, aliases, summary, content, source_file)
SELECT
  i,
  format('Bệnh demo %s', i),
  jsonb_build_array(format('BenhDemo%s', i)),
  'Dữ liệu mẫu bệnh cho môi trường demo',
  jsonb_build_object('overview', format('Mô tả bệnh demo %s', i), 'lang', 'vi'),
  'seed_vietnam_families_demo.sql'
FROM generate_series(1,30) AS g(i);

INSERT INTO drugs (source_index, title, aliases, summary, content, source_file)
SELECT
  i,
  format('Thuốc demo %s', i),
  jsonb_build_array(format('ThuocDemo%s', i)),
  'Dữ liệu mẫu thuốc cho môi trường demo',
  jsonb_build_object('indications', format('Chỉ định demo %s', i), 'lang', 'vi'),
  'seed_vietnam_families_demo.sql'
FROM generate_series(1,30) AS g(i);

INSERT INTO vaccines (source_index, title, aliases, summary, content, source_file)
SELECT
  i,
  format('Vaccine demo %s', i),
  jsonb_build_array(format('VaccineDemo%s', i)),
  'Dữ liệu mẫu vaccine cho môi trường demo',
  jsonb_build_object('prevents_disease', format('Ngừa bệnh demo %s', i), 'lang', 'vi'),
  'seed_vietnam_families_demo.sql'
FROM generate_series(1,30) AS g(i);

COMMIT;
