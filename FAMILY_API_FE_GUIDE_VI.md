# Tài Liệu Gọi Family API Cho FE

Tài liệu này mô tả cách FE gọi Family APIs theo đúng backend hiện tại.

Mục tiêu:
- Giữ tối đa các endpoint đang có.
- Backend chủ yếu đã sửa `request/response`, không mở thêm một bộ Family API mới.
- FE chỉ cần map lại đúng endpoint thật và đúng shape dữ liệu.

## 1. Nguyên tắc chung

- Hầu hết Family APIs cần `Authorization: Bearer <access_token>`. **Ngoại lệ:** `GET /families/invite/preview` (public).
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

/** Preview mã mời công khai (QR / deep-link). Không cần Bearer. */
export interface FamilyInvitePreview {
  family_name: string;
  invite_code: string;
  /** false nếu mã hết hạn, đã dùng, hoặc đã bị thay (rotate) */
  valid: boolean;
  /** ISO-8601; hết hạn theo cấu hình server (mặc định ~24h mỗi lần tạo/rotate) */
  expires_at: string;
}

/** Profile trong family chưa gắn tài khoản — dùng sau khi nhập mã mời (đã login). */
export interface LinkableFamilyProfile {
  profile_id: string;
  health_profile_id: string | null;
  full_name: string;
  dob?: string | null;
  gender?: string | null;
  avatar_url?: string | null;
  /** Thường là SHADOW hoặc PENDING_LINK */
  status: string | null;
  linked_user_id: null;
}

export interface ListLinkableProfilesResponse {
  family_id: string;
  family_name: string;
  invite_code: string;
  profiles: LinkableFamilyProfile[];
}

export interface LinkInviteProfileResponse {
  success: boolean;
  family_id: string;
  profile_id: string;
  health_profile_id: string | null;
  linked_user_id: string;
  membership_created: boolean;
  post_login_flow_completed: boolean;
}
```

Ghi chú:
- Nếu UI đang dùng `role` để hiển thị quan hệ gia đình, hãy đổi sang:
  - `displayRole = relation_role ?? role`
- `GET /families` có thể trả `invites = null`.
- `GET /families/{family_id}` là response detail đầy đủ hơn.
- **Mã mời công khai** (`invite_code` trên family): backend lưu dưới dạng token **dùng một lần** và có **thời gian hết hạn**. Sau khi một user **join** (`POST /families/join`) hoặc **link vào profile có sẵn** (`POST /families/invite/link-profile`) thành công, mã đó **không** dùng lại được; OWNER cần **rotate** để tạo mã mới nếu muốn mời tiếp bằng link/QR.
- **Proxy profile** tạo bởi `POST /families/{family_id}/profiles` (chưa có `linked_user_id`) được gán `status = SHADOW` để hiện trong flow **claim profile** (mục 4.10.4).

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
| Preview mã QR / deep-link (trước login) | `GET /families/invite/preview?invite_code=...` | **Không** cần `Authorization` |
| Join bằng mã mời công khai | `POST /families/join` với `invite_code` | Cần Bearer; mã **single-use**, có `expires_at` |
| Danh sách profile chưa có account (theo mã mời) | `GET /families/invite/linkable-profiles?invite_code=...` | Cần Bearer; mã còn **PENDING** + chưa hết hạn |
| Gắn tài khoản hiện tại vào profile có sẵn | `POST /families/invite/link-profile` | Body: `invite_code`, `profile_id`; **consume** mã; giữ `health_profile` cũ |
| Đổi mã mời công khai (OWNER) | `POST /families/{family_id}/invite/rotate` | Invalidates mã đang hiển thị, cấp mã + TTL mới |
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

### 4.10. Join bằng mã mời công khai (invite code / QR / deep-link)

Backend quản lý **mã mời công khai** như một token riêng (không chỉ là field tĩnh trên family):

| Hành vi | Ý nghĩa cho FE |
|--------|----------------|
| **Single-use** | Một mã chỉ cho **một lần** join thành công. Sau đó mã **hết hiệu lực** — user khác gửi cùng mã sẽ nhận `404`. |
| **Có hạn** | Mỗi mã có `expires_at`. Hết hạn → preview có `valid: false` và join trả `404`. Thời lượng mặc định do server (thường ~24h; có thể cấu hình env backend). |
| **Đồng bộ với OWNER** | Field `invite_code` trên `GET /families`, `GET /families/{id}`, response `POST /families` luôn là mã **đang active** (còn hạn + chưa consume). Sau khi ai đó join xong, mã đó **không còn dùng được**; để share tiếp, OWNER gọi **rotate** (mục 4.11). |

#### 4.10.1. Preview — hiển thị trước khi login (màn landing / QR)

- **Không** gửi `Authorization`.
- Có **rate limit** theo IP (tránh quét mã).

```http
GET /families/invite/preview?invite_code=ABC123
```

Response `200`:

```json
{
  "family_name": "Phan Family",
  "invite_code": "ABC123",
  "valid": true,
  "expires_at": "2026-03-30T12:00:00Z"
}
```

- `valid: false` khi mã không còn dùng được (hết hạn, đã join, hoặc đã bị OWNER rotate). FE vẫn có thể hiển thị `family_name` + `expires_at` để báo “Mã không còn hiệu lực”.
- `404` khi **không** tồn tại mã đó (sai/không có trong hệ thống).

Gợi ý UX: nếu `valid === false`, CTA là “Yêu cầu mã mới từ chủ gia đình” thay vì điều hướng login join.

#### 4.10.2. Join — bắt buộc đã đăng nhập

```http
POST /families/join
Authorization: Bearer <access_token>
```

Body:

```json
{
  "invite_code": "ABC123",
  "full_name": "Nguyễn Văn C"
}
```

- `full_name` vẫn cần khi user **chưa** có personal profile (giữ nguyên rule cũ).

Response `200`:

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

- User **đã là member** gửi lại cùng mã (đã consume) → `409` (conflict).
- Mã sai / hết hạn / đã dùng → `404`.

#### 4.10.3. Flow gợi ý (QR)

1. Quét QR → mở app với `invite_code` trong query → gọi `GET /families/invite/preview`.
2. Nếu `valid` → hiển thị tên gia đình + thời hạn; nút “Tham gia” → login/register → `POST /families/join`.

#### 4.10.4. “Tôi đã có gia đình” — chọn profile chưa có tài khoản (claim)

Dùng khi OWNER đã tạo **proxy profile** trong family (người chưa có app); user mới đăng nhập nhập mã mời và **chọn đúng dòng** trong danh sách để gắn `linked_user_id` vào profile + `health_profile` **đã có**, không tạo profile trống mới.

**Bước 1 — danh sách profile claim được**

```http
GET /families/invite/linkable-profiles?invite_code=ABC123
Authorization: Bearer <access_token>
```

Response `200`: `family_id`, `family_name`, `invite_code`, `profiles[]` (`profile_id`, `health_profile_id`, `full_name`, `dob`, `gender`, `avatar_url`, `status`, `linked_user_id` luôn `null`). Chỉ gồm profile **trong đúng family của mã**, `linked_user_id` null, `status` là `SHADOW` hoặc `PENDING_LINK`, chưa xóa.

**Bước 2 — gắn account vào profile đã chọn**

```http
POST /families/invite/link-profile
Authorization: Bearer <access_token>
```

```json
{
  "invite_code": "ABC123",
  "profile_id": "bf94402d-5f25-4d07-847d-cff4b2ac1111"
}
```

Response `200`: `success`, `family_id`, `profile_id`, `health_profile_id`, `linked_user_id`, `membership_created` (thường `false` nếu proxy đã có membership), `post_login_flow_completed: true`.

- Mã mời **single-use**: sau `link-profile` thành công, lần gọi tiếp với cùng mã → `410` hoặc `404` tùy trạng thái token.
- `410 Gone`: mã hết hạn / không còn PENDING (đã dùng, revoke, rotate) — áp dụng rõ cho hai endpoint này.
- `409`: user **đã là member** family đó; profile đã có người link; profile không thuộc family của mã; profile không ở trạng thái claim được.

**So với `POST /families/join`:** `join` tạo/ghi nhận **personal profile** của user rồi thêm membership; `link-profile` **không** tạo profile mới — chỉ link vào `profile_id` đã có.

### 4.11. Đổi mã mời công khai (OWNER — sau khi mã cũ hết dùng hoặc lộ mã)

Chỉ **OWNER** gọi được.

```http
POST /families/{family_id}/invite/rotate
Authorization: Bearer <access_token>
```

Response trả **full family contract** (giống `GET /families/{family_id}`): trong đó `invite_code` là **mã mới**, kèm TTL mới.

- Mã cũ lập tức **không** còn join được (`404` khi join/preview `valid: false` tùy trạng thái lưu).

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
- `404`: family/invite/profile không tồn tại; **join bằng `invite_code`**: mã sai, hết hạn, đã dùng (single-use), hoặc đã rotate
- `410`: **linkable-profiles / link-profile** — mã không còn dùng được (hết hạn, đã consume, revoked, rotate)
- `409`: đã là member, đã có pending invite, conflict nghiệp vụ; **link-profile**: profile đã link, không đúng family, không claim được; **linkable-profiles**: user đã là member family đó

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

### E. Join bằng mã mời công khai (QR / link)

1. (Không login) `GET /families/invite/preview?invite_code=...` — hiển thị tên gia đình + `valid` + `expires_at`.
2. User đăng nhập xong → một trong hai:
   - **Tài khoản mới / vào family bằng personal profile:** `POST /families/join` với `invite_code` (+ `full_name` nếu chưa có personal profile).
   - **Đã có sẵn proxy profile trong family:** `GET /families/invite/linkable-profiles` → chọn dòng → `POST /families/invite/link-profile`.
3. Nếu thành công: refresh `GET /families`; **mã hiện tại không dùng lại** cho người khác.
4. OWNER muốn mời thêm người bằng link mới: `POST /families/{family_id}/invite/rotate`, lấy `invite_code` mới từ response để share/QR.

## 8. Tóm tắt ngắn cho FE

- Không cần đợi backend mở thêm bộ endpoint mới như `/family-invites`, `/users/search-by-phone`, `/families/my`, `/members/proxy-profile`.
- FE nên dùng các endpoint backend hiện có:
  - `POST /families`
  - `GET /families`
  - `GET /families/{family_id}`
  - `GET /families/invites`
  - `POST /families/{family_id}/invite-by-phone`
  - `GET /families/invite/preview` (public — preview mã công khai)
  - `GET /families/invite/linkable-profiles` (đã login — danh sách profile chưa account)
  - `POST /families/invite/link-profile` (đã login — claim profile + consume mã)
  - `POST /families/join` (invite code **single-use** + có hạn; inbox vẫn dùng `action` + `invite_id`)
  - `POST /families/{family_id}/invite/rotate` (OWNER — tạo mã mới)
  - `POST /families/{family_id}/profiles`
  - `GET /families/{family_id}/members`
  - `GET /profiles/{profile_id}`
  - `GET /profiles/{profile_id}/health`
- Để hiển thị quan hệ gia đình, ưu tiên `relation_role`.
- Để xử lý quyền trong family, đọc `role`.
