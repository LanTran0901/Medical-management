# Family API FE Guide

Tai lieu nay mo ta cach FE goi Family APIs theo backend hien tai.

Muc tieu:
- Giữ toi da endpoints dang co.
- FE khong can doi flow lon theo huong tao them nhieu APIs moi.
- Backend da uu tien sua request/response de gan voi nhu cau UI Family.

## 1. Nguyen tac chung

- Tat ca Family APIs deu can `Authorization: Bearer <access_token>`.
- `phone_number` phai gui theo format E.164. Vi du:
  - `+84901234567`
  - `+14155550123`
- Backend hien tai giu `role` cho quyen trong family:
  - `OWNER`
  - `ADMIN`
  - `MEMBER`
- Neu UI can hien thi quan he gia dinh nhu `father`, `mother`, `son`, `daughter`, `nephew` thi dung field `relation_role`.
- FE van co the gui `role: "father"` hoac `role: "mother"` trong cac flow moi/invite/proxy-profile.
  Backend se tu map noi bo thanh:
  - `role = MEMBER`
  - `relation_role = "father"` hoac `"mother"`

## 2. Response shape FE nen dung

FE nen map theo shape sau:

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

Ghi chu quan trong:
- Neu UI dang dung `role` de hien thi quan he gia dinh, hay doi sang:
  - `displayRole = relation_role ?? role`
- `GET /families` co the tra `invites = null`.
- `GET /families/{family_id}` moi la response detail, co the kem `invites`.

## 3. Mapping tu UI requirement sang backend hien tai

| UI muon | Backend thuc te | Ghi chu |
|---|---|---|
| Tao family | `POST /families` | Dung ngay endpoint hien co |
| Danh sach family cua toi | `GET /families` | Khong co `/families/my` |
| Chi tiet 1 family | `GET /families/{family_id}` | Tra `members`; `invites` chi day du cho OWNER/ADMIN |
| Xem inbox loi moi | `GET /families/invites` | Khong dung `/family-invites` |
| Tim user theo SDT | `POST /families/{family_id}/invite-by-phone` voi `dry_run=true` | Khong co `GET /users/search-by-phone` rieng |
| Moi thanh vien | `POST /families/{family_id}/invite-by-phone` voi `dry_run=false` | Tao pending invite |
| Chap nhan loi moi | `POST /families/join` voi `action=accept` | Khong co `/family-invites/{id}/accept` |
| Tu choi loi moi | `POST /families/join` voi `action=reject` | Khong co `/family-invites/{id}/reject` |
| Tao proxy profile | `POST /families/{family_id}/profiles` | Khong co `/members/proxy-profile` |
| Lay danh sach members | `GET /families/{family_id}/members` | Co the dung thay cho member list trong detail screen |
| Chi tiet member | Chua co route rieng | Dung `GET /families/{family_id}` hoac `GET /families/{family_id}/members`, sau do dung `profile.id` neu can call them |

## 4. Cac flow FE nen goi

### 4.1 Tao gia dinh

Endpoint:

```http
POST /families
```

Body FE nen gui:

```json
{
  "name": "Phan Family",
  "address": "So nha, duong, phuong, quan",
  "avatar_url": "https://cdn.example.com/family-avatar.jpg",
  "owner_profile_full_name": "Phan Van A"
}
```

Backend van support body cu de tuong thich:

```json
{
  "family_name": "Phan Family",
  "full_name": "Phan Van A"
}
```

Response:

```json
{
  "id": "fam_001",
  "name": "Phan Family",
  "address": "So nha, duong, phuong, quan",
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
        "full_name": "Phan Van A",
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

### 4.2 Danh sach gia dinh cua toi

Endpoint:

```http
GET /families
```

Response:
- Tra `Family[]`
- Moi item da co `members`
- `invites` thuong se la `null`

FE co the dung endpoint nay thay cho:
- `GET /families/my`

### 4.3 Chi tiet gia dinh

Endpoint:

```http
GET /families/{family_id}
```

Dung cho:
- Header family detail
- Danh sach members
- Quick setup
- Lay `invite_code` neu OWNER muon copy/join code

Response:
- Tra `Family`
- Co `members`
- Co `invites` neu current user la `OWNER` hoac `ADMIN`
- Neu current user la `MEMBER`, `invites` co the la `[]`

### 4.4 Xem loi moi vao gia dinh

Endpoint:

```http
GET /families/invites?status=pending&page=1&limit=20
```

Khong dung:

```http
GET /family-invites
```

Response:

```json
[
  {
    "id": "invite_001",
    "family_id": "fam_002",
    "family_name": "Nha Bac Hai",
    "family_avatar_url": "https://cdn.example.com/fam-2.jpg",
    "family_member_count": 3,
    "user_id": "user_010",
    "phone_number": "+84901234567",
    "role": "MEMBER",
    "relation_role": "nephew",
    "status": "pending",
    "invited_by": "user_020",
    "inviter_name": "Nguyen Van Hai",
    "inviter_role": "OWNER",
    "invited_at": "2026-03-29T03:00:00Z",
    "responded_at": null
  }
]
```

Luu y:
- UI hien thi vai tro quan he bang `relation_role`
- `role` la quyen trong family, khong phai quan he hien thi

### 4.5 Tim user theo so dien thoai

Backend hien tai khong tach endpoint rieng `GET /users/search-by-phone`.

FE dung:

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

Response khi tim thay:

```json
{
  "dry_run": true,
  "found": true,
  "user": {
    "id": "user_010",
    "full_name": "Nguyen Thi Binh",
    "phone_number": "+84901234567",
    "avatar_url": "https://cdn.example.com/u-10.jpg",
    "has_account": true
  },
  "invite": null
}
```

Response khi khong tim thay:

```json
{
  "dry_run": true,
  "found": false,
  "user": null,
  "invite": null
}
```

### 4.6 Moi thanh vien vao gia dinh

Backend dung cung endpoint voi search:

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

Neu FE da biet chac `user_id`, co the gui them `user_id`.
Neu chua biet user, backend van cho phep moi theo `phone_number`.

Luu y:
- FE co the gui `role: "mother"` hoac `role: "father"`
- Backend se map noi bo thanh:
  - `role = MEMBER`
  - `relation_role = "mother"` hoac `"father"`

Response:

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

### 4.7 Tao ho so nguoi than khong co account

Endpoint:

```http
POST /families/{family_id}/profiles
```

Body FE nen gui:

```json
{
  "role": "father",
  "profile": {
    "full_name": "Nguyen Van Ba",
    "date_of_birth": "1960-09-15",
    "gender": "male",
    "height_cm": 165,
    "weight_kg": 62,
    "address": "Quan 1, TP HCM",
    "avatar_url": "https://cdn.example.com/member-ba.jpg"
  },
  "health_profile": {
    "blood_type": "B+",
    "chronic_conditions": ["Tieu duong type 2"],
    "allergies": []
  }
}
```

Response:

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
    "full_name": "Nguyen Van Ba",
    "date_of_birth": "1960-09-15",
    "gender": "male",
    "height_cm": 165,
    "weight_kg": 62,
    "address": "Quan 1, TP HCM",
    "avatar_url": "https://cdn.example.com/member-ba.jpg"
  },
  "health_profile": {
    "blood_type": "B+",
    "chronic_conditions": ["Tieu duong type 2"],
    "allergies": []
  }
}
```

### 4.8 Chap nhan loi moi vao gia dinh

Khong dung:

```http
POST /family-invites/{invite_id}/accept
```

Dung:

```http
POST /families/join
```

Body:

```json
{
  "action": "accept",
  "invite_id": "invite_001",
  "full_name": "Nguyen Thi Binh"
}
```

`full_name` can gui khi user duoc moi chua co personal profile.

Response:

```json
{
  "success": true,
  "invite_id": "invite_001",
  "status": "accepted",
  "family_member_id": "fm_011"
}
```

### 4.9 Tu choi loi moi vao gia dinh

Khong dung:

```http
POST /family-invites/{invite_id}/reject
```

Dung:

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

### 4.10 Join bang invite code

Flow cu van duoc giu de backward compatibility.

Endpoint:

```http
POST /families/join
```

Body:

```json
{
  "invite_code": "ABC123",
  "full_name": "Nguyen Van C"
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

## 5. Member detail screen nen goi API nao

Backend hien tai chua co:

```http
GET /families/{family_id}/members/{member_id}
```

FE nen dung 1 trong 2 cach sau:

### Cach 1: Dung data da embed trong family detail

Goi:

```http
GET /families/{family_id}
```

Sau do tim member theo `members[].id`.

Hop cho:
- Member list
- Tab thong tin nhanh
- Tab suc khoe co ban

### Cach 2: Neu can refresh du lieu profile/health rieng

Lay `profile.id` tu `FamilyMember.profile.id`, roi goi:

```http
GET /profiles/{profile_id}
GET /profiles/{profile_id}/health
```

## 6. Ma loi FE can xu ly

- `400`: body khong hop le, sai format phone, thieu field can thiet
- `403`: khong du quyen
- `404`: family/invite/profile khong ton tai
- `409`: da la member, da co pending invite, conflict nghiep vu

## 7. Luong goi API de FE implement

### A. Create family

1. `POST /families`
2. Dung response tra ve de render man family detail ngay

### B. Tim SDT va moi vao family

1. `POST /families/{family_id}/invite-by-phone` voi `dry_run=true`
2. Neu tim thay hoac FE van muon moi theo SDT thi goi lai cung endpoint voi `dry_run=false`
3. Refresh inbox hoac family detail neu can

### C. Nguoi duoc moi vao app va chap nhan

1. `GET /families/invites?status=pending`
2. `POST /families/join` voi `action=accept` hoac `action=reject`
3. Sau khi accept:
   - reload `GET /families`
   - hoac reload `GET /families/{family_id}`

### D. Tao proxy profile

1. `POST /families/{family_id}/profiles`
2. Neu can reload danh sach members, goi `GET /families/{family_id}` hoac `GET /families/{family_id}/members`

## 8. Tom tat quan trong cho FE

- Khong can doi sang bo endpoint moi nhu `/family-invites`, `/users/search-by-phone`, `/families/my`, `/members/proxy-profile`.
- FE nen dung cac endpoint backend hien co:
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
- De hien thi quan he gia dinh, uu tien `relation_role`.
- De xu ly quyen trong family, doc `role`.
