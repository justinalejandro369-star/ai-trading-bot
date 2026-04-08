/**
 * Auth API helpers.
 * Login uses FormData — backend expects OAuth2PasswordRequestForm (form encoding).
 */

export async function loginUser(
  username: string,
  password: string,
): Promise<{ ok: boolean; error?: string }> {
  const form = new FormData()
  form.append('username', username)
  form.append('password', password)

  try {
    const response = await fetch('/auth/login', {
      method: 'POST',
      body: form,
      credentials: 'include',
    })

    if (response.ok) {
      return { ok: true }
    }

    let errorMsg = 'Invalid credentials'
    try {
      const data = (await response.json()) as { detail?: string }
      if (data.detail) errorMsg = data.detail
    } catch {
      // ignore json parse errors
    }
    return { ok: false, error: errorMsg }
  } catch {
    return { ok: false, error: 'Network error. Please try again.' }
  }
}

export async function logoutUser(): Promise<void> {
  await fetch('/auth/logout', {
    method: 'POST',
    credentials: 'include',
  })
}

export async function getMe(): Promise<{ username: string } | null> {
  try {
    const response = await fetch('/auth/me', {
      credentials: 'include',
    })
    if (!response.ok) return null
    return response.json() as Promise<{ username: string }>
  } catch {
    return null
  }
}
