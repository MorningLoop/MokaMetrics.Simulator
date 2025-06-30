import { create } from 'zustand'

interface AuthState {
  isAuthenticated: boolean
  user: { username: string } | null
  login: (username: string, password: string) => boolean
  logout: () => void
}

// Hard-coded credentials
const VALID_CREDENTIALS = {
  username: 'admin',
  password: 'Vmware2!'
}

export const useAuthStore = create<AuthState>((set) => ({
  isAuthenticated: false,
  user: null,
  login: (username: string, password: string) => {
    if (username === VALID_CREDENTIALS.username && password === VALID_CREDENTIALS.password) {
      set({
        isAuthenticated: true,
        user: { username }
      })
      return true
    }
    return false
  },
  logout: () => {
    set({
      isAuthenticated: false,
      user: null
    })
  }
}))
