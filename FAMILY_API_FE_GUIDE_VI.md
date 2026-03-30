# Tài Liệu Gọi Family API Cho FE

Tài liệu này mô tả cách FE gọi Family APIs theo đúng backend hiện tại.

Mục tiêu:
- Giữ tối đa các endpoint đang có.
- Backend chủ yếu đã sửa `request/response`, không mở thêm một bộ Family API mới.
- FE chỉ cần map lại đúng endpoint thật và đúng shape dữ liệu.

## 1. Nguyên tắc chung

- Tất cả Family APIs đều cần `Authorization: Bearer <access_token>`.
- `phone_number` phải gửi theo format E.164. Ví dụ:
  - `+84901234567`
  - `+14155550123`
- Backend hiện tại giữ `role` để biểu diễn quyền trong family:
  - `OWNER`
  - `ADMIN`
  - `MEMBER`
- Nếu UI cần hiển thị quan hệ gia đình như `father`, `mother`, `son`, `daughter`, `nephew` thì dùng `relation_role`.
- FE vẫn có thể gửi `role: "father"` hoặc `role: "mother"` trong flow mời/tạo proxy profile.
  Backend sẽ tự map nội bộ thành:
  - `role = MEMBER`
  - `relation_role = "father"` hoặc `"mother"`

## 2. Shape dữ liệu FE nên dùng

```ts
type FamilyPermissionRole = "OWNER" | "ADMIN" | "MEMBER";
type FamilyInviteStatus = "pending" | "accepted" | "rejected";

export interface FamilyMemberProfile {
  id: string;
  full_name: string;
  date_of_birth?: string | null;
  gender?: string | null;
  height_cm?: number | null;
  weight_kg?: number | null;
  address?: string | null;
  avatar_url?: string | null;
}

export interface FamilyMemberHealthProfile {
  blood_type?: string | null;
  chronic_conditions: string[];
  allergies: string[];
}

export interface FamilyMember {
  id: string;
  family_id: string;
  user_id?: string | null;
  role: FamilyPermissionRole;
  relation_role?: string | null;
  is_owner?: boolean;
  is_self?: boolean;
  joined_at?: string | null;
  profile: FamilyMemberProfile;
  health_profile: FamilyMemberHealthProfile;
}

export interface FamilyInvite {
  id: string;
  family_id: string;
  phone_number?: string | null;
  user_id?: string | null;
  role: FamilyPermissionRole;
  relation_role?: string | null;
  status: FamilyInviteStatus;
  invited_by: string;
  invited_at: string;
  responded_at?: string | null;
}

export interface FamilyInviteInbox extends FamilyInvite {
  family_name: string;
  family_avatar_url?: string | null;
  family_member_count: number;
  inviter_name?: string | null;
  inviter_role?: FamilyPermissionRole | null;
}

export interface Family {
  id: string;
  name: string;
  address?: string | null;
  avatar_url?: string | null;
  created_by?: string | null;
  created_at: string;
  invite_code?: string | null;
  members: FamilyMember[];
  invites?: FamilyInvite[] | null;
}
```

Ghi chú:
- Nếu UI đang dùng `role` để hiển thị quan hệ gia đình, hãy đổi sang:
  - `displayRole = relation_role ?? role`
- `GET /families` có thể trả `invites = null`.
- `GET /families/{family_id}` là response detail đầy đủ hơn.

## 3. Mapping từ yêu cầu UI sang backend hiện tại

| FE muốn gọi | Backend thực tế | Ghi chú |
|---|---|---|
| Tạo family | `POST /families` | Dùng endpoint hiện có |
| Danh sách family của tôi | `GET /families` | Không có `/families/my` |
| Chi tiết 1 family | `GET /families/{family_id}` | Có `members`, có thể có `invites` |
| Xem inbox lời mời | `GET /families/invites` | Không dùng `/family-invites` |
| Tìm user theo số điện thoại | `POST /families/{family_id}/invite-by-phone` với `dry_run=true` | Không có `GET /users/search-by-phone` riêng |
| Mời thành viên | `POST /families/{family_id}/invite-by-phone` với `dry_run=false` | Tạo pending invite |
| Chấp nhận lời mời | `POST /families/join` với `action=accept` | Không có `/family-invites/{id}/accept` |
| Từ chối lời mời | `POST /families/join` với `action=reject` | Không có `/family-invites/{id}/reject` |
| Tạo proxy profile | `POST /families/{family_id}/profiles` | Không có `/members/proxy-profile` |
| Danh sách members | `GET /families/{family_id}/members` | Dùng cho list member |
| Chi tiết member | Chưa có route riêng | Dùng `GET /families/{family_id}` hoặc `GET /families/{family_id}/members` |

## 4. Các flow FE nên gọi

### 4.1. Tạo gia đình

Endpoint:

```http
POST /families
```

Body FE nên gửi:

```json
{
  "name": "Phan Family",
  "address": "Số nhà, đường, phường, quận",
  "avatar_url": "https://cdn.example.com/family-avatar.jpg",
  "owner_profile_full_name": "Phan Văn A"
}
```

Backend vẫn hỗ trợ body cũ để tương thích:

```json
{
  "family_name": "Phan Family",
  "full_name": "Phan Văn A"
}
```

Response mẫu:

```json
{
  "id": "fam_001",
  "name": "Phan Family",
  "address": "Số nhà, đường, phường, quận",
  "avatar_url": "https://cdn.example.com/family-avatar.jpg",
  "created_by": "user_001",
  "created_at": "2026-03-29T10:00:00Z",
  "invite_code": "ABC123",
  "members": [
    {
      "id": "fm_001",
      "family_id": "fam_001",
      "user_id": "user_001",
      "role": "OWNER",
      "relation_role": null,
      "is_owner": true,
      "is_self": true,
      "joined_at": "2026-03-29T10:00:00Z",
      "profile": {
        "id": "profile_001",
        "full_name": "Phan Văn A",
        "date_of_birth": null,
        "gender": null,
        "height_cm": null,
        "weight_kg": null,
        "address": null,
        "avatar_url": null
      },
      "health_profile": {
        "blood_type": null,
        "chronic_conditions": [],
        "allergies": []
      }
    }
  ],
  "invites": []
}
```

### 4.2. Danh sách gia đình của tôi

Endpoint:

```http
GET /families
```

Ghi chú:
- Dùng endpoint này thay cho `GET /families/my`
- Response là `Family[]`
- Mỗi item đã có `members`
- `invites` thường là `null`

### 4.3. Chi tiết gia đình

Endpoint:

```http
GET /families/{family_id}
```

Dùng cho:
- Header family detail
- Danh sách members
- Quick setup
- Lấy `invite_code` nếu OWNER muốn copy hoặc dùng join code

Ghi chú:
- Response là `Family`
- Có `members`
- Có `invites` nếu current user là `OWNER` hoặc `ADMIN`

### 4.4. Xem lời mời vào gia đình

Endpoint:

```http
GET /families/invites?status=pending&page=1&limit=20
```

Không dùng:

```http
GET /family-invites
```

Response mẫu:

```json
[
  {
    "id": "invite_001",
    "family_id": "fam_002",
    "family_name": "Nhà Bác Hai",
    "family_avatar_url": "https://cdn.example.com/fam-2.jpg",
    "family_member_count": 3,
    "user_id": "user_010",
    "phone_number": "+84901234567",
    "role": "MEMBER",
    "relation_role": "nephew",
    "status": "pending",
    "invited_by": "user_020",
    "inviter_name": "Nguyễn Văn Hải",
    "inviter_role": "OWNER",
    "invited_at": "2026-03-29T03:00:00Z",
    "responded_at": null
  }
]
```

Lưu ý:
- UI hiển thị vai trò quan hệ bằng `relation_role`
- `role` là quyền trong family, không phải nhãn quan hệ để hiển thị

### 4.5. Tìm user theo số điện thoại

Backend hiện tại không có endpoint riêng `GET /users/search-by-phone`.

FE dùng:

```http
POST /families/{family_id}/invite-by-phone
```

Body:

```json
{
  "phone_number": "+84901234567",
  "dry_run": true
}
```

Response khi tìm thấy:

```json
{
  "dry_run": true,
  "found": true,
  "user": {
    "id": "user_010",
    "full_name": "Nguyễn Thị Bình",
    "phone_number": "+84901234567",
    "avatar_url": "https://cdn.example.com/u-10.jpg",
    "has_account": true
  },
  "invite": null
}
```

Response khi không tìm thấy:

```json
{
  "dry_run": true,
  "found": false,
  "user": null,
  "invite": null
}
```

### 4.6. Mời thành viên vào gia đình

Backend dùng cùng endpoint với flow search:

```http
POST /families/{family_id}/invite-by-phone
```

Body canonical:

```json
{
  "phone_number": "+84901234567",
  "user_id": "user_010",
  "role": "mother",
  "dry_run": false
}
```

Lưu ý:
- FE có thể gửi `role: "mother"` hoặc `role: "father"`
- Backend sẽ map nội bộ thành:
  - `role = MEMBER`
  - `relation_role = "mother"` hoặc `"father"`

Response mẫu:

```json
{
  "dry_run": false,
  "found": null,
  "user": null,
  "invite": {
    "id": "invite_001",
    "family_id": "fam_001",
    "user_id": "user_010",
    "phone_number": "+84901234567",
    "role": "MEMBER",
    "relation_role": "mother",
    "status": "pending",
    "invited_by": "user_001",
    "invited_at": "2026-03-29T10:10:00Z",
    "responded_at": null
  }
}
```

### 4.7. Tạo hồ sơ người thân không có account

Endpoint:

```http
POST /families/{family_id}/profiles
```

Body FE nên gửi:

```json
{
  "role": "father",
  "profile": {
    "full_name": "Nguyễn Văn Ba",
    "date_of_birth": "1960-09-15",
    "gender": "male",
    "height_cm": 165,
    "weight_kg": 62,
    "address": "Quận 1, TP HCM",
    "avatar_url": "https://cdn.example.com/member-ba.jpg"
  },
  "health_profile": {
    "blood_type": "B+",
    "chronic_conditions": ["Tiểu đường type 2"],
    "allergies": []
  }
}
```

Response mẫu:

```json
{
  "id": "fm_010",
  "family_id": "fam_001",
  "user_id": null,
  "role": "MEMBER",
  "relation_role": "father",
  "is_owner": false,
  "is_self": false,
  "joined_at": "2026-03-29T10:20:00Z",
  "profile": {
    "id": "profile_010",
    "full_name": "Nguyễn Văn Ba",
    "date_of_birth": "1960-09-15",
    "gender": "male",
    "height_cm": 165,
    "weight_kg": 62,
    "address": "Quận 1, TP HCM",
    "avatar_url": "https://cdn.example.com/member-ba.jpg"
  },
  "health_profile": {
    "blood_type": "B+",
    "chronic_conditions": ["Tiểu đường type 2"],
    "allergies": []
  }
}
```

### 4.8. Chấp nhận lời mời vào gia đình

Không dùng:

```http
POST /family-invites/{invite_id}/accept
```

Dùng:

```http
POST /families/join
```

Body:

```json
{
  "action": "accept",
  "invite_id": "invite_001",
  "full_name": "Nguyễn Thị Bình"
}
```

`full_name` cần gửi nếu user được mời chưa có personal profile.

Response:

```json
{
  "success": true,
  "invite_id": "invite_001",
  "status": "accepted",
  "family_member_id": "fm_011"
}
```

### 4.9. Từ chối lời mời vào gia đình

Không dùng:

```http
POST /family-invites/{invite_id}/reject
```

Dùng:

```http
POST /families/join
```

Body:

```json
{
  "action": "reject",
  "invite_id": "invite_001"
}
```

Response:

```json
{
  "success": true,
  "invite_id": "invite_001",
  "status": "rejected",
  "family_member_id": null
}
```

### 4.10. Join bằng invite code

Flow cũ vẫn được giữ để backward compatibility.

Endpoint:

```http
POST /families/join
```

Body:

```json
{
  "invite_code": "ABC123",
  "full_name": "Nguyễn Văn C"
}
```

Response:

```json
{
  "mode": "invite_code",
  "family_id": "fam_001",
  "family_name": "Phan Family",
  "profile_id": "profile_011",
  "membership_id": "fm_011",
  "message": "Joined family"
}
```

## 5. Member detail screen nên gọi API nào

Backend hiện tại chưa có:

```http
GET /families/{family_id}/members/{member_id}
```

FE nên dùng 1 trong 2 cách sau:

### Cách 1: Dùng data đã embed trong family detail

Gọi:

```http
GET /families/{family_id}
```

Sau đó tìm member theo `members[].id`.

Hợp cho:
- Member list
- Tab thông tin nhanh
- Tab sức khỏe cơ bản

### Cách 2: Nếu cần refresh dữ liệu profile/health riêng

Lấy `profile.id` từ `FamilyMember.profile.id`, rồi gọi:

```http
GET /profiles/{profile_id}
GET /profiles/{profile_id}/health
```

## 6. Mã lỗi FE cần xử lý

- `400`: body không hợp lệ, sai format phone, thiếu field cần thiết
- `403`: không đủ quyền
- `404`: family/invite/profile không tồn tại
- `409`: đã là member, đã có pending invite, conflict nghiệp vụ

## 7. Luồng gọi API FE nên implement

### A. Tạo family

1. `POST /families`
2. Dùng response trả về để render màn family detail ngay

### B. Tìm số điện thoại và mời vào family

1. `POST /families/{family_id}/invite-by-phone` với `dry_run=true`
2. Nếu tìm thấy hoặc FE vẫn muốn mời theo số điện thoại thì gọi lại cùng endpoint với `dry_run=false`
3. Refresh inbox hoặc family detail nếu cần

### C. Người được mời vào app và phản hồi

1. `GET /families/invites?status=pending`
2. `POST /families/join` với `action=accept` hoặc `action=reject`
3. Sau khi accept:
   - reload `GET /families`
   - hoặc reload `GET /families/{family_id}`

### D. Tạo proxy profile

1. `POST /families/{family_id}/profiles`
2. Nếu cần reload danh sách members, gọi `GET /families/{family_id}` hoặc `GET /families/{family_id}/members`

## 8. Tóm tắt ngắn cho FE

- Không cần đợi backend mở thêm bộ endpoint mới như `/family-invites`, `/users/search-by-phone`, `/families/my`, `/members/proxy-profile`.
- FE nên dùng các endpoint backend hiện có:
  - `POST /families`
  - `GET /families`
  - `GET /families/{family_id}`
  - `GET /families/invites`
  - `POST /families/{family_id}/invite-by-phone`
  - `POST /families/join`
  - `POST /families/{family_id}/profiles`
  - `GET /families/{family_id}/members`
  - `GET /profiles/{profile_id}`
  - `GET /profiles/{profile_id}/health`
- Để hiển thị quan hệ gia đình, ưu tiên `relation_role`.
- Để xử lý quyền trong family, đọc `role`.
