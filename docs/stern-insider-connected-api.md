# Stern Insider Connected API Documentation

This document describes the Stern Insider Connected API as reverse-engineered from the [stern-home-leaderboard](https://github.com/brombomb/stern-home-leaderboard) project. This API allows access to registered pinball machines, high scores, and player information.

## Overview

The Stern Insider Connected platform consists of several API endpoints:

| Base URL | Purpose |
|----------|---------|
| `https://insider.sternpinball.com` | Authentication |
| `https://cms.prd.sternpinball.io/api/v1/portal` | Content Management (machines, scores) |
| `https://api.prd.sternpinball.io/api/v1/portal` | Game data (teams, avatars) |

## Authentication

### Login

Stern uses a Next.js-based authentication system. The login endpoint expects a specific format.

**Endpoint:** `POST https://insider.sternpinball.com/login`

**Headers:**
```http
Content-Type: text/plain;charset=UTF-8
Next-Action: 9d2cf818afff9e2c69368771b521d93585a10433
Next-Router-State-Tree: %5B%22%22%2C%7B%22children%22%3A%5B%22login%22%2C%7B%22children%22%3A%5B%22__PAGE__%22%2C%7B%7D%2C%22%2Flogin%22%2C%22refresh%22%5D%7D%5D%7D%2Cnull%2Cnull%2Ctrue%5D
```

**Request Body:** JSON array containing username and password
```json
["username", "password"]
```

**Response:**
- On success, the response body contains `"authenticated": true`
- The `Set-Cookie` header contains `spb-insider-token` which is the Bearer token for subsequent requests

### Token Management

- **Token Expiry:** 30 minutes (recommended refresh interval)
- **Storage:** The token should be stored along with any cookies received during login
- **Usage:** Include as Bearer token in Authorization header

### Request Headers for API Calls

All authenticated API requests should include:

```http
Accept: application/json, text/plain, */*
Accept-Language: en-US,en;q=0.5
Accept-Encoding: gzip, deflate, br, zstd
Referer: https://insider.sternpinball.com/
Content-Type: application/json
Cache-Control: max-age=604800, no-cache, no-store
Origin: https://insider.sternpinball.com
DNT: 1
Sec-GPC: 1
Connection: keep-alive
Sec-Fetch-Dest: empty
Sec-Fetch-Mode: cors
Sec-Fetch-Site: cross-site
Pragma: no-cache
Authorization: Bearer {token}
Cookie: {session_cookies_from_login}
Location: {"country":"US","state":"CO","stateName":"Colorado","continent":"NA"}
User-Agent: Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:142.0) Gecko/20100101 Firefox/142.0
```

The `Location` header contains a JSON object with the user's location information. This may affect which data is returned.

---

## API Endpoints

### 1. Get Registered Machines

Retrieves all machines registered to the authenticated user's account.

**Endpoint:** `GET https://cms.prd.sternpinball.io/api/v1/portal/user_registered_machines/?group_type=home`

**Query Parameters:**
| Parameter | Value | Description |
|-----------|-------|-------------|
| `group_type` | `home` | Filter to home-registered machines |

**Response:**
```json
{
  "user": {
    "machines": [
      {
        "id": 12345,
        "model": {
          "title": {
            "name": "Foo Fighters Premium"
          }
        },
        "address": {
          "location_id": 67890
        },
        "archived": false
      }
    ]
  }
}
```

**Response Fields:**
| Field | Type | Description |
|-------|------|-------------|
| `id` | number | Unique machine identifier |
| `model.title.name` | string | Display name of the pinball machine |
| `address.location_id` | number | Location identifier (used for team/avatar lookups) |
| `archived` | boolean | Whether the machine is archived (should be filtered out) |

---

### 2. Get Machine Details

Retrieves detailed information about a specific machine.

**Endpoint:** `GET https://cms.prd.sternpinball.io/api/v1/portal/game_machines/{machine_id}`

**Path Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `machine_id` | number | The machine ID from the machines list |

**Response:** Detailed machine object (structure extends the basic machine object from the list endpoint)

---

### 3. Get High Scores

Retrieves the leaderboard/high scores for a specific machine.

**Endpoint:** `GET https://cms.prd.sternpinball.io/api/v1/portal/game_machine_high_scores/?machine_id={machine_id}`

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `machine_id` | number | The machine ID to get scores for |

**Response:**
```json
{
  "high_score": [
    {
      "id": "abc123",
      "score": "1000000000",
      "user": {
        "username": "player1",
        "name": "John Doe",
        "initials": "JD"
      }
    },
    {
      "id": "def456",
      "score": "500000000",
      "user": {
        "username": "player2",
        "name": "Jane Smith",
        "initials": "JS"
      }
    }
  ]
}
```

**Response Fields:**
| Field | Type | Description |
|-------|------|-------------|
| `high_score` | array | Array of score entries, ordered by rank |
| `high_score[].id` | string | Unique score identifier |
| `high_score[].score` | string | Score value as a numeric string |
| `high_score[].user.username` | string | Player's username |
| `high_score[].user.name` | string | Player's display name |
| `high_score[].user.initials` | string | Player's initials (typically 2-3 characters) |

**Notes:**
- Scores are returned as strings to handle large numbers
- The array is typically ordered by score descending (highest first)

---

### 4. Get Game Teams (Player Avatars)

Retrieves team/player information including avatars for a specific location.

**Endpoint:** `GET https://api.prd.sternpinball.io/api/v1/portal/game_teams/?location_id={location_id}`

> **Note:** This endpoint uses a different base URL (`api.prd` instead of `cms.prd`)

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `location_id` | number | The location ID from a machine's address |

**Response:**
```json
{
  "team": [
    {
      "username": "player1",
      "avatar_url": "https://example.com/avatar1.png",
      "background_color": "#FF5733"
    },
    {
      "username": "player2",
      "avatar_url": "https://example.com/avatar2.png",
      "background_color": "#3498DB"
    }
  ]
}
```

**Response Fields:**
| Field | Type | Description |
|-------|------|-------------|
| `team` | array | Array of team members at this location |
| `team[].username` | string | Player's username (matches high score entries) |
| `team[].avatar_url` | string | URL to the player's avatar image |
| `team[].background_color` | string | CSS hex colour for the player's background |

---

## Error Handling

### HTTP Status Codes

| Status | Meaning | Action |
|--------|---------|--------|
| 200 | Success | Process response |
| 401 | Unauthorised | Re-authenticate and retry |
| 403 | Forbidden | Re-authenticate and retry |
| 404 | Not Found | Resource doesn't exist |
| 500 | Server Error | Retry after delay |

### Retry Logic

When receiving a 401 or 403 response:
1. Perform a fresh login to obtain a new token
2. Retry the original request with the new token
3. Limit retries to 2 attempts to avoid infinite loops

---

## Implementation Considerations

### Rate Limiting

- Recommended minimum polling interval: **30 minutes**
- The reference implementation uses a default of 60 minutes

### Data Caching

Consider caching:
- Machine list (changes infrequently)
- Player avatars (keyed by username, changes infrequently)
- High scores (poll periodically for updates)

### Score Change Detection

To detect new high scores:
1. Store previous scores with unique identifiers
2. Compare current scores against stored scores
3. Generate score ID using: `score.id` or fallback to `"{username}-{score}"`
4. New entries not in previous set are new scores

### Location Header

The `Location` header appears to be used for region-specific data. Configure based on your location:

```json
{
  "country": "US",
  "state": "CO",
  "stateName": "Colorado",
  "continent": "NA"
}
```

---

## Data Structures Summary

### Machine
```typescript
interface Machine {
  id: number;
  model: {
    title: {
      name: string;
    };
  };
  address: {
    location_id: number;
  };
  archived: boolean;
}
```

### HighScore
```typescript
interface HighScore {
  id: string;
  score: string;  // Numeric string
  user: {
    username: string;
    name: string;
    initials: string;
  };
}
```

### TeamMember
```typescript
interface TeamMember {
  username: string;
  avatar_url: string;
  background_color: string;  // CSS hex colour
}
```

---

## Security Notes

- Never expose Stern credentials to client-side code
- Use a backend proxy to handle authentication
- Store tokens securely and refresh before expiry
- All communication should use HTTPS

---

## References

- Source: [stern-home-leaderboard](https://github.com/brombomb/stern-home-leaderboard)
- Stern Insider Connected: https://insider.sternpinball.com
