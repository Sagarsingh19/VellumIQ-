import api from "./api";
import { LoginPayload, SignupPayload, LoginResponse } from "@/types";

export const authService = {
  async login(payload: LoginPayload): Promise<LoginResponse> {
    // Send form URLencoded data as required by OAuth2PasswordRequestForm
    const formData = new URLSearchParams();
    formData.append("username", payload.email);
    formData.append("password", payload.password);

    const response = await api.post("/auth/login", formData, {
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
      },
    });
    
    const data = response.data;
    if (data.access_token) {
      localStorage.setItem("token", data.access_token);
      localStorage.setItem("user", JSON.stringify(data.user));
    }
    return data;
  },

  async signup(payload: SignupPayload): Promise<any> {
    const response = await api.post("/auth/signup", {
      email: payload.email,
      password: payload.password,
      organization_name: payload.organization_name,
    });
    return response.data;
  },

  logout() {
    localStorage.removeItem("token");
    localStorage.removeItem("user");
    window.location.href = "/login";
  },

  getCurrentUser() {
    if (typeof window !== "undefined") {
      const user = localStorage.getItem("user");
      return user ? JSON.parse(user) : null;
    }
    return null;
  }
};
