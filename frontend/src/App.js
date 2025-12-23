import React, { useState, useEffect, createContext, useContext } from "react";
import { BrowserRouter, Routes, Route, Navigate, Link, useNavigate, useLocation, useSearchParams } from "react-router-dom";
import axios from "axios";
import { Toaster, toast } from "sonner";
import { 
  Cpu, Wallet, Activity, Clock, Server, Globe, Zap, 
  LogOut, Menu, X, ChevronRight, Play, Square, 
  DollarSign, BarChart3, Settings, Users, Home,
  Plus, RefreshCw, CreditCard, FileText, AlertCircle, Bell,
  Shield, Mail, Smartphone, Copy, Check, Eye, EyeOff, Sparkles,
  MessageSquare, Send, Bitcoin, Search, Monitor
} from "lucide-react";
import { Button } from "./components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "./components/ui/card";
import { Input } from "./components/ui/input";
import { Label } from "./components/ui/label";
import { Badge } from "./components/ui/badge";
import { Progress } from "./components/ui/progress";
import { 
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue 
} from "./components/ui/select";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter
} from "./components/ui/dialog";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "./components/ui/tabs";
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger
} from "./components/ui/dropdown-menu";
import { Textarea } from "./components/ui/textarea";
import "./App.css";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// ============== NOTIFICATION BELL COMPONENT ==============
const NotificationBell = ({ token }) => {
  const [notifications, setNotifications] = useState([]);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    fetchNotifications();
    const interval = setInterval(fetchNotifications, 10000); // كل 10 ثوانٍ
    return () => clearInterval(interval);
  }, [token]);

  const fetchNotifications = async () => {
    if (!token) return;
    try {
      const res = await axios.get(`${API}/notifications`, { headers: { Authorization: `Bearer ${token}` } });
      setNotifications(res.data);
      
      // Show toast for urgent unread notifications
      const urgent = res.data.filter(n => n.urgent && !n.read);
      urgent.forEach(n => {
        toast.warning(n.title, { description: n.message, duration: 10000 });
      });
    } catch (e) {}
  };

  const markAsRead = async (id) => {
    try {
      await axios.post(`${API}/notifications/${id}/read`, {}, { headers: { Authorization: `Bearer ${token}` } });
      fetchNotifications();
    } catch (e) {}
  };

  const unreadCount = notifications.filter(n => !n.read).length;

  const getIcon = (type) => {
    switch(type) {
      case 'auto_stop': return '🛑';
      case 'low_balance_warning': return '⚠️';
      case 'seamless_failover': return '🔄';
      default: return '🔔';
    }
  };

  return (
    <DropdownMenu open={open} onOpenChange={setOpen}>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon" className="relative" data-testid="notification-bell">
          <Bell className="w-5 h-5" />
          {unreadCount > 0 && (
            <span className="absolute -top-1 -right-1 w-5 h-5 bg-[#FF4757] text-white text-xs rounded-full flex items-center justify-center">
              {unreadCount}
            </span>
          )}
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-80 bg-[#12121A] border-[#1E1E2E]">
        <div className="p-3 border-b border-[#1E1E2E]">
          <h3 className="font-semibold">الإشعارات</h3>
        </div>
        <div className="max-h-80 overflow-y-auto">
          {notifications.length === 0 ? (
            <div className="p-4 text-center text-[#8B8B9E]">لا توجد إشعارات</div>
          ) : (
            notifications.slice(0, 10).map((n) => (
              <DropdownMenuItem 
                key={n.id} 
                className={`p-3 cursor-pointer ${!n.read ? 'bg-[#00D4FF]/5' : ''}`}
                onClick={() => markAsRead(n.id)}
              >
                <div className="flex gap-3 w-full">
                  <span className="text-xl">{getIcon(n.type)}</span>
                  <div className="flex-1 min-w-0">
                    <p className={`text-sm font-medium ${n.urgent ? 'text-[#FF4757]' : ''}`}>{n.title}</p>
                    <p className="text-xs text-[#8B8B9E] truncate">{n.message}</p>
                    <p className="text-xs text-[#8B8B9E] mt-1">{new Date(n.created_at).toLocaleString('ar')}</p>
                  </div>
                  {!n.read && <div className="w-2 h-2 bg-[#00D4FF] rounded-full"></div>}
                </div>
              </DropdownMenuItem>
            ))
          )}
        </div>
      </DropdownMenuContent>
    </DropdownMenu>
  );
};

// Auth Context
const AuthContext = createContext(null);

const useAuth = () => useContext(AuthContext);

const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [token, setToken] = useState(localStorage.getItem("token"));

  useEffect(() => {
    if (token) {
      fetchUser();
    } else {
      setLoading(false);
    }
  }, [token]);

  const fetchUser = async () => {
    try {
      const res = await axios.get(`${API}/auth/me`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setUser(res.data);
    } catch (e) {
      localStorage.removeItem("token");
      setToken(null);
    } finally {
      setLoading(false);
    }
  };

  const login = async (email, password) => {
    const res = await axios.post(`${API}/auth/login`, { email, password });
    // التحقق من 2FA
    if (res.data.requires_2fa) {
      return res.data; // سيعالج في LoginPage
    }
    localStorage.setItem("token", res.data.token);
    localStorage.setItem("user", JSON.stringify(res.data.user));
    setToken(res.data.token);
    setUser(res.data.user);
    return res.data;
  };

  const register = async (email, password, name) => {
    const res = await axios.post(`${API}/auth/register`, { email, password, name });
    localStorage.setItem("token", res.data.token);
    localStorage.setItem("user", JSON.stringify(res.data.user));
    setToken(res.data.token);
    setUser(res.data.user);
    return res.data;
  };

  // REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
  const loginWithGoogle = () => {
    const redirectUrl = window.location.origin + '/dashboard';
    window.location.href = `https://auth.emergentagent.com/?redirect=${encodeURIComponent(redirectUrl)}`;
  };

  const setAuthFromGoogle = (userData, sessionToken) => {
    localStorage.setItem("token", sessionToken);
    localStorage.setItem("user", JSON.stringify(userData));
    setToken(sessionToken);
    setUser(userData);
  };

  const logout = () => {
    localStorage.removeItem("token");
    setToken(null);
    setUser(null);
  };

  const refreshUser = async () => {
    if (token) await fetchUser();
  };

  return (
    <AuthContext.Provider value={{ user, token, loading, login, register, logout, refreshUser, loginWithGoogle, setAuthFromGoogle }}>
      {children}
    </AuthContext.Provider>
  );
};

// Auth Callback - يعالج الرجوع من Google
const AuthCallback = () => {
  const { setAuthFromGoogle } = useAuth();
  const navigate = useNavigate();
  const hasProcessed = React.useRef(false);

  useEffect(() => {
    if (hasProcessed.current) return;
    hasProcessed.current = true;

    const processGoogleAuth = async () => {
      try {
        // استخراج session_id من URL
        const hash = window.location.hash;
        const sessionId = hash.split('session_id=')[1]?.split('&')[0];
        
        if (!sessionId) {
          toast.error("فشل تسجيل الدخول");
          navigate('/login');
          return;
        }

        // جلب بيانات المستخدم من Emergent Auth
        const response = await fetch('https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data', {
          headers: { 'X-Session-ID': sessionId }
        });

        if (!response.ok) {
          throw new Error('Failed to get session data');
        }

        const data = await response.json();
        
        // حفظ/تحديث المستخدم في قاعدة البيانات
        const backendRes = await axios.post(`${API}/auth/google`, {
          email: data.email,
          name: data.name,
          picture: data.picture,
          google_id: data.id
        });

        // تسجيل الدخول
        setAuthFromGoogle(backendRes.data.user, backendRes.data.token);
        
        toast.success(`مرحباً ${data.name}! 🎉`);
        
        // تنظيف URL والانتقال للوحة التحكم
        window.history.replaceState({}, '', '/dashboard');
        navigate('/dashboard', { replace: true });
        
      } catch (error) {
        console.error('Google auth error:', error);
        toast.error("فشل تسجيل الدخول بجوجل");
        navigate('/login');
      }
    };

    processGoogleAuth();
  }, []);

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#0A0A0F]">
      <div className="text-center">
        <div className="spinner mb-4"></div>
        <p className="text-[#8B8B9E]">جاري تسجيل الدخول...</p>
      </div>
    </div>
  );
};

// Protected Route
const ProtectedRoute = ({ children }) => {
  const { user, loading } = useAuth();
  
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#0A0A0F]">
        <div className="spinner"></div>
      </div>
    );
  }
  
  if (!user) {
    return <Navigate to="/login" replace />;
  }
  
  return children;
};

// Landing Page
const LandingPage = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [gpus, setGpus] = useState([]);
  const [regions, setRegions] = useState([]);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [gpuRes, regionRes] = await Promise.all([
        axios.get(`${API}/gpus`),
        axios.get(`${API}/regions`)
      ]);
      setGpus(gpuRes.data.slice(0, 6));
      setRegions(regionRes.data);
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <div className="min-h-screen gradient-mesh">
      {/* Navbar */}
      <nav className="fixed top-0 left-0 right-0 z-50 bg-[#0A0A0F]/80 backdrop-blur-xl border-b border-[#1E1E2E]">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <Link to="/" className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-[#00D4FF] to-[#0099CC] flex items-center justify-center">
                <Cpu className="w-6 h-6 text-[#0A0A0F]" />
              </div>
              <span className="text-xl font-bold">GPU Cloud Pro</span>
            </Link>
            <div className="flex items-center gap-4">
              {user ? (
                <Button onClick={() => navigate("/dashboard")} className="btn-neon" data-testid="go-to-dashboard-btn">
                  Dashboard
                </Button>
              ) : (
                <>
                  <Button variant="ghost" onClick={() => navigate("/login")} data-testid="login-nav-btn">
                    Login
                  </Button>
                  <Button onClick={() => navigate("/register")} className="btn-neon" data-testid="register-nav-btn">
                    Get Started
                  </Button>
                </>
              )}
            </div>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="pt-32 pb-20 px-4">
        <div className="max-w-7xl mx-auto text-center">
          <Badge className="mb-6 bg-[#00D4FF]/10 text-[#00D4FF] border-[#00D4FF]/30 px-4 py-2">
            <Zap className="w-4 h-4 mr-2" />
            Powered by NVIDIA GPUs
          </Badge>
          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold mb-6 leading-tight">
            GPU Computing
            <span className="block neon-text">بالثانية</span>
          </h1>
          <p className="text-lg sm:text-xl text-[#8B8B9E] max-w-2xl mx-auto mb-10">
            استأجر كروت شاشة عالية الأداء للذكاء الاصطناعي، التدريب، والرندر. 
            ادفع فقط مقابل ما تستخدمه - بالثانية الواحدة.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Button 
              onClick={() => navigate(user ? "/marketplace" : "/register")} 
              className="btn-neon text-lg px-8 py-6"
              data-testid="hero-start-btn"
            >
              ابدأ الآن
              <ChevronRight className="w-5 h-5 ml-2" />
            </Button>
            <Button 
              variant="outline" 
              onClick={() => navigate("/marketplace")}
              className="btn-outline text-lg px-8 py-6"
              data-testid="hero-browse-btn"
            >
              تصفح GPUs
            </Button>
          </div>
        </div>
      </section>

      {/* Stats Section */}
      <section className="py-16 px-4 border-y border-[#1E1E2E]">
        <div className="max-w-7xl mx-auto">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
            {[
              { label: "GPUs متاحة", value: gpus.length + "+", icon: Server },
              { label: "مناطق عالمية", value: regions.length, icon: Globe },
              { label: "أقل سعر/ساعة", value: "$0.49", icon: DollarSign },
              { label: "وقت التشغيل", value: "99.9%", icon: Activity }
            ].map((stat, i) => (
              <div key={i} className="text-center animate-fade-in" style={{ animationDelay: `${i * 100}ms` }}>
                <stat.icon className="w-8 h-8 text-[#00D4FF] mx-auto mb-3" />
                <div className="text-3xl font-bold text-white mb-1">{stat.value}</div>
                <div className="text-[#8B8B9E] text-sm">{stat.label}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Regions Section */}
      <section className="py-20 px-4">
        <div className="max-w-7xl mx-auto">
          <h2 className="text-3xl font-bold text-center mb-4">مناطق عالمية</h2>
          <p className="text-[#8B8B9E] text-center mb-12">اختر الموقع الأقرب لك للحصول على أقل زمن استجابة</p>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {regions.map((region, i) => (
              <Card key={i} className="gpu-card" data-testid={`region-card-${i}`}>
                <CardContent className="p-6">
                  <div className="flex items-center gap-3 mb-4">
                    <Globe className="w-6 h-6 text-[#00D4FF]" />
                    <span className="font-semibold">{region.name}</span>
                  </div>
                  <div className="space-y-3">
                    <div className="flex justify-between">
                      <span className="text-[#8B8B9E]">GPUs متاحة</span>
                      <span className="font-mono text-[#00FF88]">{region.available_gpus}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-[#8B8B9E]">متوسط Latency</span>
                      <span className={`font-mono ${region.avg_latency < 30 ? 'text-[#00FF88]' : region.avg_latency < 50 ? 'text-[#FFB800]' : 'text-[#FF4757]'}`}>
                        {region.avg_latency}ms
                      </span>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* Featured GPUs */}
      <section className="py-20 px-4 bg-[#12121A]/50">
        <div className="max-w-7xl mx-auto">
          <h2 className="text-3xl font-bold text-center mb-4">GPUs المتاحة</h2>
          <p className="text-[#8B8B9E] text-center mb-12">اختر من بين أحدث كروت الشاشة</p>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {gpus.map((gpu, i) => (
              <Card key={gpu.id} className="gpu-card" data-testid={`gpu-card-${i}`}>
                <CardContent className="p-6">
                  <div className="flex items-start justify-between mb-4">
                    <div>
                      <h3 className="font-semibold text-lg">{gpu.name}</h3>
                      <Badge variant="outline" className="mt-2 text-[#00D4FF] border-[#00D4FF]/30">
                        {gpu.vram}GB VRAM
                      </Badge>
                    </div>
                    <div className="status-dot available"></div>
                  </div>
                  <div className="space-y-2 mb-4">
                    <div className="flex justify-between text-sm">
                      <span className="text-[#8B8B9E]">المنطقة</span>
                      <span>{gpu.region}</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-[#8B8B9E]">Latency</span>
                      <span className={gpu.latency < 30 ? 'text-[#00FF88]' : gpu.latency < 50 ? 'text-[#FFB800]' : 'text-[#FF4757]'}>
                        {gpu.latency}ms
                      </span>
                    </div>
                  </div>
                  <div className="flex items-center justify-between pt-4 border-t border-[#1E1E2E]">
                    <div>
                      <span className="text-2xl font-bold text-[#00D4FF]">${gpu.price_per_hour}</span>
                      <span className="text-[#8B8B9E] text-sm">/ساعة</span>
                    </div>
                    <Button 
                      size="sm" 
                      className="btn-neon"
                      onClick={() => navigate(user ? "/marketplace" : "/register")}
                    >
                      استئجار
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
          <div className="text-center mt-10">
            <Button 
              variant="outline" 
              onClick={() => navigate("/marketplace")}
              className="btn-outline"
              data-testid="view-all-gpus-btn"
            >
              عرض جميع GPUs
              <ChevronRight className="w-4 h-4 ml-2" />
            </Button>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-12 px-4 border-t border-[#1E1E2E]">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-[#00D4FF] to-[#0099CC] flex items-center justify-center">
              <Cpu className="w-5 h-5 text-[#0A0A0F]" />
            </div>
            <span className="font-bold">GPU Cloud Pro</span>
          </div>
          <div className="text-[#8B8B9E] text-sm">
            © 2024 GPU Cloud Pro. جميع الحقوق محفوظة.
          </div>
        </div>
      </footer>
    </div>
  );
};

// Auth Pages
const LoginPage = () => {
  const [showEmailLogin, setShowEmailLogin] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [requires2FA, setRequires2FA] = useState(false);
  const [twoFactorCode, setTwoFactorCode] = useState("");
  const [twoFactorMethod, setTwoFactorMethod] = useState("totp");
  const [showPassword, setShowPassword] = useState(false);
  const { login, loginWithGoogle } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const result = await login(email, password);
      if (result?.requires_2fa) {
        setRequires2FA(true);
        setTwoFactorMethod(result.two_factor_method || "totp");
        toast.info("مطلوب رمز المصادقة الثنائية");
      } else {
        toast.success("تم تسجيل الدخول بنجاح");
        navigate("/dashboard");
      }
    } catch (err) {
      toast.error(err.response?.data?.detail || "فشل تسجيل الدخول");
    } finally {
      setLoading(false);
    }
  };

  const handle2FASubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const res = await axios.post(`${API}/auth/login/2fa`, {
        email,
        password,
        two_factor_code: twoFactorCode,
        two_factor_method: twoFactorMethod
      });
      
      localStorage.setItem("token", res.data.token);
      localStorage.setItem("user", JSON.stringify(res.data.user));
      toast.success("تم تسجيل الدخول بنجاح");
      navigate("/dashboard");
      window.location.reload();
    } catch (err) {
      toast.error(err.response?.data?.detail || "رمز غير صحيح");
    } finally {
      setLoading(false);
    }
  };

  // عرض نموذج 2FA
  if (requires2FA) {
    return (
      <div className="min-h-screen gradient-mesh flex items-center justify-center px-4">
        <Card className="w-full max-w-md gpu-card">
          <CardHeader className="text-center">
            <div className="w-16 h-16 rounded-full bg-[#00D4FF]/20 flex items-center justify-center mx-auto mb-4">
              <Shield className="w-8 h-8 text-[#00D4FF]" />
            </div>
            <CardTitle className="text-2xl">المصادقة الثنائية</CardTitle>
            <CardDescription>أدخل رمز التحقق</CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handle2FASubmit} className="space-y-4">
              <div className="space-y-2">
                <Label>رمز التحقق</Label>
                <Input
                  type="text"
                  placeholder="000000"
                  value={twoFactorCode}
                  onChange={(e) => setTwoFactorCode(e.target.value.replace(/\D/g, "").slice(0, 6))}
                  className="text-center text-2xl font-mono tracking-widest"
                  maxLength={6}
                  autoFocus
                />
              </div>
              <Button type="submit" className="w-full btn-neon" disabled={loading || twoFactorCode.length !== 6}>
                {loading ? "جاري التحقق..." : "تأكيد"}
              </Button>
              <Button type="button" variant="ghost" className="w-full" onClick={() => { setRequires2FA(false); setTwoFactorCode(""); }}>
                رجوع
              </Button>
            </form>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen gradient-mesh flex items-center justify-center px-4">
      <Card className="w-full max-w-md gpu-card" data-testid="login-card">
        <CardHeader className="text-center">
          <Link to="/" className="inline-flex items-center gap-2 justify-center mb-4">
            <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-[#00D4FF] to-[#0099CC] flex items-center justify-center">
              <Cpu className="w-6 h-6 text-[#0A0A0F]" />
            </div>
          </Link>
          <CardTitle className="text-2xl">مرحباً بك!</CardTitle>
          <CardDescription>سجل دخول بضغطة واحدة</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* زر جوجل الرئيسي - الطريقة الأسهل */}
          <Button 
            onClick={loginWithGoogle}
            className="w-full h-14 text-lg bg-white hover:bg-gray-100 text-gray-800 border border-gray-300"
            data-testid="google-login-btn"
          >
            <svg className="w-6 h-6 mr-3" viewBox="0 0 24 24">
              <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
              <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
              <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
              <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
            </svg>
            الدخول بحساب Google
          </Button>

          {!showEmailLogin ? (
            <div className="text-center">
              <button 
                onClick={() => setShowEmailLogin(true)}
                className="text-sm text-[#8B8B9E] hover:text-[#00D4FF] underline"
              >
                أو سجل دخول بالبريد الإلكتروني
              </button>
            </div>
          ) : (
            <>
              <div className="relative">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-[#1E1E2E]"></div>
                </div>
                <div className="relative flex justify-center text-xs">
                  <span className="bg-[#12121A] px-2 text-[#8B8B9E]">أو</span>
                </div>
              </div>

              <form onSubmit={handleSubmit} className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="email">البريد الإلكتروني</Label>
                  <Input
                    id="email"
                    type="email"
                    placeholder="your@email.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                    data-testid="login-email-input"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="password">كلمة المرور</Label>
                  <div className="relative">
                    <Input
                      id="password"
                      type={showPassword ? "text" : "password"}
                      placeholder="••••••••"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      required
                      data-testid="login-password-input"
                      className="pr-10"
                    />
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      className="absolute right-1 top-1/2 -translate-y-1/2 h-7 w-7"
                      onClick={() => setShowPassword(!showPassword)}
                    >
                      {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </Button>
                  </div>
                </div>
                <Button type="submit" className="w-full btn-neon" disabled={loading} data-testid="login-submit-btn">
                  {loading ? "جاري التحميل..." : "تسجيل الدخول"}
                </Button>
              </form>
            </>
          )}

          <div className="text-center text-sm text-[#8B8B9E]">
            ليس لديك حساب؟{" "}
            <Link to="/register" className="text-[#00D4FF] hover:underline">
              سجل الآن
            </Link>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

const RegisterPage = () => {
  const [showEmailRegister, setShowEmailRegister] = useState(false);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [generatedPassword, setGeneratedPassword] = useState(null);
  const [copied, setCopied] = useState(false);
  const { register, loginWithGoogle } = useAuth();
  const navigate = useNavigate();

  // توليد كلمة مرور مقترحة
  const generatePassword = async () => {
    try {
      const res = await axios.get(`${API}/auth/generate-password`);
      setPassword(res.data.password);
      setShowPassword(true);
      toast.success("تم توليد كلمة مرور قوية!");
    } catch (e) {
      toast.error("فشل توليد كلمة المرور");
    }
  };

  const copyPassword = () => {
    navigator.clipboard.writeText(password);
    setCopied(true);
    toast.success("تم نسخ كلمة المرور!");
    setTimeout(() => setCopied(false), 2000);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await register(email, password, name);
      toast.success("تم إنشاء الحساب بنجاح");
      navigate("/dashboard");
    } catch (err) {
      toast.error(err.response?.data?.detail || "فشل إنشاء الحساب");
    } finally {
      setLoading(false);
    }
  };

  // تسجيل سريع بالبريد فقط
  const handleQuickRegister = async () => {
    if (!email) {
      toast.error("أدخل بريدك الإلكتروني");
      return;
    }
    setLoading(true);
    try {
      const res = await axios.post(`${API}/auth/quick-register`, { 
        email, 
        name: name || email.split("@")[0]
      });
      
      if (res.data.generated_password) {
        setGeneratedPassword(res.data.generated_password);
        toast.success("تم إنشاء حسابك! احفظ كلمة المرور");
      } else {
        localStorage.setItem("token", res.data.token);
        localStorage.setItem("user", JSON.stringify(res.data.user));
        navigate("/dashboard");
      }
    } catch (err) {
      toast.error(err.response?.data?.detail || "فشل إنشاء الحساب");
    } finally {
      setLoading(false);
    }
  };

  // إذا تم توليد كلمة مرور - أظهر نافذة الحفظ
  if (generatedPassword) {
    return (
      <div className="min-h-screen gradient-mesh flex items-center justify-center px-4">
        <Card className="w-full max-w-md gpu-card">
          <CardHeader className="text-center">
            <div className="w-16 h-16 rounded-full bg-[#00FF88]/20 flex items-center justify-center mx-auto mb-4">
              <Check className="w-8 h-8 text-[#00FF88]" />
            </div>
            <CardTitle className="text-2xl">تم إنشاء حسابك! 🎉</CardTitle>
            <CardDescription>احفظ كلمة المرور الخاصة بك</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="p-4 rounded-lg bg-[#FFB800]/10 border border-[#FFB800]/30">
              <p className="text-sm text-[#FFB800] mb-2 flex items-center gap-2">
                <AlertCircle className="w-4 h-4" />
                مهم جداً - احفظ كلمة المرور
              </p>
              <div className="flex items-center gap-2">
                <code className="flex-1 p-3 rounded bg-[#0A0A0F] text-lg font-mono text-[#00D4FF]">
                  {generatedPassword}
                </code>
                <Button
                  variant="outline"
                  size="icon"
                  onClick={() => {
                    navigator.clipboard.writeText(generatedPassword);
                    toast.success("تم نسخ كلمة المرور!");
                  }}
                >
                  <Copy className="w-4 h-4" />
                </Button>
              </div>
            </div>
            <Button
              className="w-full btn-neon"
              onClick={() => {
                localStorage.setItem("token", generatedPassword);
                window.location.href = "/login";
              }}
            >
              فهمت، سجل دخولي
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen gradient-mesh flex items-center justify-center px-4">
      <Card className="w-full max-w-md gpu-card" data-testid="register-card">
        <CardHeader className="text-center">
          <Link to="/" className="inline-flex items-center gap-2 justify-center mb-4">
            <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-[#00D4FF] to-[#0099CC] flex items-center justify-center">
              <Cpu className="w-6 h-6 text-[#0A0A0F]" />
            </div>
          </Link>
          <CardTitle className="text-2xl">إنشاء حساب</CardTitle>
          <CardDescription>ابدأ باستخدام GPU Cloud Pro</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* زر جوجل الرئيسي - الطريقة الأسهل */}
          <Button 
            onClick={loginWithGoogle}
            className="w-full h-14 text-lg bg-white hover:bg-gray-100 text-gray-800 border border-gray-300"
            data-testid="google-register-btn"
          >
            <svg className="w-6 h-6 mr-3" viewBox="0 0 24 24">
              <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
              <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
              <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
              <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
            </svg>
            التسجيل بحساب Google
          </Button>

          {!showEmailRegister ? (
            <div className="text-center">
              <button 
                onClick={() => setShowEmailRegister(true)}
                className="text-sm text-[#8B8B9E] hover:text-[#00D4FF] underline"
              >
                أو سجل بالبريد الإلكتروني
              </button>
            </div>
          ) : (
            <>
              <div className="relative">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-[#1E1E2E]"></div>
                </div>
                <div className="relative flex justify-center text-xs">
                  <span className="bg-[#12121A] px-2 text-[#8B8B9E]">أو</span>
                </div>
              </div>

              {/* تسجيل سريع بالبريد */}
              <div className="p-4 rounded-lg bg-[#00D4FF]/5 border border-[#00D4FF]/20">
                <div className="flex items-center gap-2 mb-3">
                  <Sparkles className="w-5 h-5 text-[#00D4FF]" />
                  <span className="font-medium text-[#00D4FF]">تسجيل سريع</span>
                </div>
                <div className="flex gap-2">
                  <Input
                    type="email"
                    placeholder="بريدك@example.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="flex-1"
                  />
                  <Button 
                    onClick={handleQuickRegister} 
                    disabled={loading}
                    className="btn-neon whitespace-nowrap"
                  >
                    {loading ? "..." : "ابدأ"}
                  </Button>
                </div>
                <p className="text-xs text-[#8B8B9E] mt-2">سيتم إنشاء كلمة مرور آمنة تلقائياً</p>
              </div>
            </>
          )}

          <div className="text-center text-sm text-[#8B8B9E]">
            لديك حساب بالفعل؟{" "}
            <Link to="/login" className="text-[#00D4FF] hover:underline">
              سجل دخول
            </Link>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

// Dashboard Layout
const DashboardLayout = ({ children }) => {
  const { user, logout, token } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const navItems = [
    { path: "/dashboard", label: "الرئيسية", icon: Home },
    { path: "/marketplace", label: "سوق GPUs", icon: Server },
    { path: "/instances", label: "الجلسات", icon: Activity },
    { path: "/billing", label: "الفوترة", icon: Wallet },
    { path: "/security", label: "الأمان", icon: Shield },
  ];

  return (
    <div className="min-h-screen bg-[#0A0A0F] flex">
      {/* Mobile Sidebar Overlay */}
      {sidebarOpen && (
        <div 
          className="fixed inset-0 bg-black/50 z-40 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside className={`
        fixed lg:static inset-y-0 left-0 z-50
        w-64 sidebar transform transition-transform duration-300
        ${sidebarOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
      `}>
        <div className="flex flex-col h-full">
          <div className="p-4 border-b border-[#1E1E2E]">
            <Link to="/" className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-[#00D4FF] to-[#0099CC] flex items-center justify-center">
                <Cpu className="w-6 h-6 text-[#0A0A0F]" />
              </div>
              <span className="text-lg font-bold">GPU Cloud Pro</span>
            </Link>
          </div>

          <nav className="flex-1 py-4">
            {navItems.map((item) => (
              <Link
                key={item.path}
                to={item.path}
                className={`sidebar-link ${location.pathname === item.path ? 'active' : ''}`}
                onClick={() => setSidebarOpen(false)}
                data-testid={`nav-${item.path.replace('/', '')}`}
              >
                <item.icon className="w-5 h-5" />
                <span>{item.label}</span>
              </Link>
            ))}
          </nav>

          <div className="p-4 border-t border-[#1E1E2E]">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-full bg-gradient-to-br from-[#00D4FF] to-[#0099CC] flex items-center justify-center text-[#0A0A0F] font-bold">
                {user?.name?.charAt(0).toUpperCase()}
              </div>
              <div className="flex-1 min-w-0">
                <div className="font-medium truncate">{user?.name}</div>
                <div className="text-sm text-[#8B8B9E] truncate">{user?.email}</div>
              </div>
            </div>
            <Button 
              variant="ghost" 
              className="w-full justify-start text-[#8B8B9E] hover:text-white"
              onClick={() => { logout(); navigate("/"); }}
              data-testid="logout-btn"
            >
              <LogOut className="w-4 h-4 mr-2" />
              تسجيل الخروج
            </Button>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <div className="flex-1 flex flex-col min-h-screen">
        {/* Top Bar */}
        <header className="sticky top-0 z-30 bg-[#0A0A0F]/80 backdrop-blur-xl border-b border-[#1E1E2E]">
          <div className="flex items-center justify-between h-16 px-4">
            <Button
              variant="ghost"
              size="icon"
              className="lg:hidden"
              onClick={() => setSidebarOpen(true)}
            >
              <Menu className="w-6 h-6" />
            </Button>

            <div className="flex items-center gap-4 ml-auto">
              {/* Notifications Bell */}
              <NotificationBell token={token} />
              
              <div className="flex items-center gap-2 px-4 py-2 rounded-lg bg-[#12121A] border border-[#1E1E2E]">
                <Wallet className="w-4 h-4 text-[#00D4FF]" />
                <span className="font-mono font-semibold text-[#00D4FF]" data-testid="balance-display">
                  ${user?.balance?.toFixed(2) || "0.00"}
                </span>
              </div>
              <Button 
                size="sm" 
                className="btn-neon"
                onClick={() => navigate("/billing")}
                data-testid="add-funds-btn"
              >
                <Plus className="w-4 h-4 mr-1" />
                شحن
              </Button>
            </div>
          </div>
        </header>

        {/* Page Content */}
        <main className="flex-1 p-4 lg:p-8">
          {children}
        </main>
      </div>
    </div>
  );
};

// Dashboard Home
const DashboardHome = () => {
  const { user, token, refreshUser } = useAuth();
  const [instances, setInstances] = useState([]);
  const [stats, setStats] = useState({ total_spent: 0, total_hours: 0 });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchActiveInstances, 5000);
    return () => clearInterval(interval);
  }, []);

  const fetchData = async () => {
    try {
      const [instancesRes, transactionsRes] = await Promise.all([
        axios.get(`${API}/instances/active`, { headers: { Authorization: `Bearer ${token}` } }),
        axios.get(`${API}/billing/transactions`, { headers: { Authorization: `Bearer ${token}` } })
      ]);
      setInstances(instancesRes.data);
      
      const spent = transactionsRes.data
        .filter(t => t.type === "usage")
        .reduce((sum, t) => sum + Math.abs(t.amount), 0);
      setStats({ total_spent: spent, total_hours: Math.round(spent / 0.5) });
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const fetchActiveInstances = async () => {
    try {
      const res = await axios.get(`${API}/instances/active`, { headers: { Authorization: `Bearer ${token}` } });
      setInstances(res.data);
    } catch (e) {}
  };

  const stopInstance = async (instanceId) => {
    try {
      await axios.post(`${API}/instances/${instanceId}/stop`, {}, { headers: { Authorization: `Bearer ${token}` } });
      toast.success("تم إيقاف الجلسة بنجاح");
      fetchData();
      refreshUser();
    } catch (e) {
      toast.error(e.response?.data?.detail || "فشل إيقاف الجلسة");
    }
  };

  if (loading) {
    return <div className="flex items-center justify-center h-64"><div className="spinner"></div></div>;
  }

  return (
    <div className="space-y-8 animate-fade-in" data-testid="dashboard-home">
      <div>
        <h1 className="text-2xl font-bold">مرحباً، {user?.name}</h1>
        <p className="text-[#8B8B9E]">إليك نظرة عامة على حسابك</p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="stat-card" data-testid="stat-balance">
          <CardContent className="p-6">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 rounded-lg bg-[#00D4FF]/10 flex items-center justify-center">
                <Wallet className="w-6 h-6 text-[#00D4FF]" />
              </div>
              <div>
                <p className="text-[#8B8B9E] text-sm">الرصيد</p>
                <p className="text-2xl font-bold text-[#00D4FF]">${user?.balance?.toFixed(2)}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="stat-card" data-testid="stat-active">
          <CardContent className="p-6">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 rounded-lg bg-[#00FF88]/10 flex items-center justify-center">
                <Activity className="w-6 h-6 text-[#00FF88]" />
              </div>
              <div>
                <p className="text-[#8B8B9E] text-sm">جلسات نشطة</p>
                <p className="text-2xl font-bold">{instances.length}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="stat-card" data-testid="stat-spent">
          <CardContent className="p-6">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 rounded-lg bg-[#FFB800]/10 flex items-center justify-center">
                <DollarSign className="w-6 h-6 text-[#FFB800]" />
              </div>
              <div>
                <p className="text-[#8B8B9E] text-sm">إجمالي الإنفاق</p>
                <p className="text-2xl font-bold">${stats.total_spent.toFixed(2)}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="stat-card" data-testid="stat-hours">
          <CardContent className="p-6">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 rounded-lg bg-[#FF4757]/10 flex items-center justify-center">
                <Clock className="w-6 h-6 text-[#FF4757]" />
              </div>
              <div>
                <p className="text-[#8B8B9E] text-sm">ساعات الاستخدام</p>
                <p className="text-2xl font-bold">{stats.total_hours}h</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Active Instances */}
      <Card className="gpu-card">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Activity className="w-5 h-5 text-[#00FF88]" />
            الجلسات النشطة
          </CardTitle>
        </CardHeader>
        <CardContent>
          {instances.length === 0 ? (
            <div className="text-center py-12 text-[#8B8B9E]">
              <Server className="w-12 h-12 mx-auto mb-4 opacity-50" />
              <p>لا توجد جلسات نشطة</p>
              <Button className="mt-4 btn-outline" onClick={() => window.location.href = "/marketplace"}>
                استئجار GPU
              </Button>
            </div>
          ) : (
            <div className="space-y-4">
              {instances.map((instance) => (
                <div key={instance.id} className="p-4 rounded-lg bg-[#0A0A0F] border border-[#1E1E2E]" data-testid={`active-instance-${instance.id}`}>
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-3">
                      <div className="status-dot available"></div>
                      <span className="font-semibold">{instance.gpu_name}</span>
                    </div>
                    <Button 
                      size="sm" 
                      variant="destructive"
                      onClick={() => stopInstance(instance.id)}
                      data-testid={`stop-instance-${instance.id}`}
                    >
                      <Square className="w-4 h-4 mr-1" />
                      إيقاف
                    </Button>
                  </div>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                    <div>
                      <span className="text-[#8B8B9E]">المدة</span>
                      <p className="font-mono">{Math.floor(instance.duration_seconds / 60)}m {instance.duration_seconds % 60}s</p>
                    </div>
                    <div>
                      <span className="text-[#8B8B9E]">التكلفة الحالية</span>
                      <p className="font-mono text-[#00D4FF]">${instance.current_cost?.toFixed(4)}</p>
                    </div>
                    <div>
                      <span className="text-[#8B8B9E]">SSH</span>
                      <p className="font-mono text-xs truncate">{instance.access_info?.ssh}</p>
                    </div>
                    <div>
                      <span className="text-[#8B8B9E]">Jupyter</span>
                      <p className="font-mono text-xs truncate">{instance.access_info?.jupyter}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

// GPU Marketplace
const MarketplacePage = () => {
  const { user, token, refreshUser } = useAuth();
  const [gpus, setGpus] = useState([]);
  const [regions, setRegions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedRegion, setSelectedRegion] = useState("all");
  const [selectedModel, setSelectedModel] = useState("all");
  const [startingGpu, setStartingGpu] = useState(null);
  const [confirmDialog, setConfirmDialog] = useState(false);
  const [selectedGpu, setSelectedGpu] = useState(null);

  useEffect(() => {
    fetchData();
  }, [selectedRegion, selectedModel]);

  const fetchData = async () => {
    try {
      let url = `${API}/gpus?status=available`;
      if (selectedRegion !== "all") url += `&region=${selectedRegion}`;
      if (selectedModel !== "all") url += `&model=${selectedModel}`;
      
      const [gpuRes, regionRes] = await Promise.all([
        axios.get(url),
        axios.get(`${API}/regions`)
      ]);
      setGpus(gpuRes.data);
      setRegions(regionRes.data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleRent = (gpu) => {
    if (!user) {
      window.location.href = "/login";
      return;
    }
    setSelectedGpu(gpu);
    setConfirmDialog(true);
  };

  const confirmRent = async () => {
    if (!selectedGpu) return;
    setStartingGpu(selectedGpu.id);
    try {
      await axios.post(`${API}/instances/start`, { gpu_id: selectedGpu.id }, { headers: { Authorization: `Bearer ${token}` } });
      toast.success("تم بدء الجلسة بنجاح!");
      refreshUser();
      fetchData();
      window.location.href = "/instances";
    } catch (e) {
      toast.error(e.response?.data?.detail || "فشل بدء الجلسة");
    } finally {
      setStartingGpu(null);
      setConfirmDialog(false);
    }
  };

  const uniqueModels = [...new Set(gpus.map(g => g.model))];

  return (
    <div className="space-y-6 animate-fade-in" data-testid="marketplace-page">
      <div>
        <h1 className="text-2xl font-bold">سوق GPUs</h1>
        <p className="text-[#8B8B9E]">اختر GPU وابدأ الاستئجار فوراً</p>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-4">
        <Select value={selectedRegion} onValueChange={setSelectedRegion}>
          <SelectTrigger className="w-48" data-testid="region-filter">
            <Globe className="w-4 h-4 mr-2" />
            <SelectValue placeholder="المنطقة" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">جميع المناطق</SelectItem>
            {regions.map(r => (
              <SelectItem key={r.name} value={r.name}>{r.name}</SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Select value={selectedModel} onValueChange={setSelectedModel}>
          <SelectTrigger className="w-48" data-testid="model-filter">
            <Cpu className="w-4 h-4 mr-2" />
            <SelectValue placeholder="الموديل" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">جميع الموديلات</SelectItem>
            {uniqueModels.map(m => (
              <SelectItem key={m} value={m}>{m}</SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Button variant="outline" onClick={fetchData} className="btn-outline">
          <RefreshCw className="w-4 h-4 mr-2" />
          تحديث
        </Button>
      </div>

      {/* GPU Grid */}
      {loading ? (
        <div className="flex items-center justify-center h-64"><div className="spinner"></div></div>
      ) : gpus.length === 0 ? (
        <Card className="gpu-card">
          <CardContent className="p-12 text-center">
            <Server className="w-16 h-16 mx-auto mb-4 text-[#8B8B9E] opacity-50" />
            <h3 className="text-lg font-semibold mb-2">لا توجد GPUs متاحة</h3>
            <p className="text-[#8B8B9E]">جرب تغيير الفلاتر أو انتظر قليلاً</p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {gpus.map((gpu) => (
            <Card key={gpu.id} className="gpu-card" data-testid={`marketplace-gpu-${gpu.id}`}>
              <CardContent className="p-6">
                <div className="flex items-start justify-between mb-4">
                  <div>
                    <h3 className="font-semibold text-lg">{gpu.name}</h3>
                    <div className="flex items-center gap-2 mt-2 flex-wrap">
                      <Badge variant="outline" className="text-[#00D4FF] border-[#00D4FF]/30">
                        {gpu.vram}GB VRAM
                      </Badge>
                      {gpu.performance && (
                        <Badge className={`
                          ${gpu.performance.tier === 'ultra' ? 'bg-[#FF4757]/20 text-[#FF4757] border-[#FF4757]/30' : ''}
                          ${gpu.performance.tier === 'premium' ? 'bg-[#FFB800]/20 text-[#FFB800] border-[#FFB800]/30' : ''}
                          ${gpu.performance.tier === 'professional' ? 'bg-[#00FF88]/20 text-[#00FF88] border-[#00FF88]/30' : ''}
                          ${gpu.performance.tier === 'high' ? 'bg-[#00D4FF]/20 text-[#00D4FF] border-[#00D4FF]/30' : ''}
                          ${gpu.performance.tier === 'mid' ? 'bg-[#8B8B9E]/20 text-[#8B8B9E] border-[#8B8B9E]/30' : ''}
                        `}>
                          {gpu.performance.tier_label}
                        </Badge>
                      )}
                    </div>
                  </div>
                  <div className="status-dot available"></div>
                </div>

                {/* Power Score */}
                {gpu.performance && (
                  <div className="mb-4 p-3 rounded-lg bg-[#0A0A0F]">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-xs text-[#8B8B9E]">مؤشر القوة</span>
                      <span className="text-sm font-bold text-[#00D4FF]">{Math.round(gpu.performance.power_score)}/100</span>
                    </div>
                    <Progress value={gpu.performance.power_score} className="h-2" />
                    <div className="flex justify-between mt-2 text-xs">
                      <div className="flex items-center gap-1">
                        <Zap className="w-3 h-3 text-[#FFB800]" />
                        <span className="text-[#8B8B9E]">AI: {gpu.performance.ai_score}%</span>
                      </div>
                      <div className="flex items-center gap-1">
                        <BarChart3 className="w-3 h-3 text-[#00FF88]" />
                        <span className="text-[#8B8B9E]">Render: {gpu.performance.render_score}%</span>
                      </div>
                    </div>
                    {gpu.performance.best_for && (
                      <div className="mt-2 text-xs text-[#8B8B9E]">
                        <span className="text-[#00D4FF]">مثالي لـ: </span>
                        {gpu.performance.best_for.slice(0, 2).join(', ')}
                      </div>
                    )}
                  </div>
                )}

                <div className="space-y-2 mb-4">
                  <div className="flex justify-between text-sm">
                    <span className="text-[#8B8B9E]">المنطقة</span>
                    <span className="flex items-center gap-1">
                      <Globe className="w-3 h-3" />
                      {gpu.region}
                    </span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-[#8B8B9E]">Latency</span>
                    <span className={gpu.latency < 30 ? 'text-[#00FF88]' : gpu.latency < 50 ? 'text-[#FFB800]' : 'text-[#FF4757]'}>
                      {gpu.latency}ms
                    </span>
                  </div>
                  {gpu.performance?.health && (
                    <div className="flex justify-between text-sm">
                      <span className="text-[#8B8B9E]">حالة الكرت</span>
                      <span className={gpu.performance.health.status === 'excellent' ? 'text-[#00FF88]' : 'text-[#FFB800]'}>
                        {gpu.performance.health.status === 'excellent' ? 'ممتاز' : 'جيد'} ({gpu.performance.health.temperature}°C)
                      </span>
                    </div>
                  )}
                </div>

                <div className="pt-4 border-t border-[#1E1E2E]">
                  <div className="flex items-center justify-between mb-4">
                    <div>
                      <span className="text-3xl font-bold text-[#00D4FF]">${gpu.price_per_hour}</span>
                      <span className="text-[#8B8B9E]">/ساعة</span>
                    </div>
                    <div className="text-right text-xs text-[#8B8B9E]">
                      <div>${(gpu.price_per_second * 60).toFixed(4)}/دقيقة</div>
                      <div>${gpu.price_per_second.toFixed(6)}/ثانية</div>
                    </div>
                  </div>
                  <Button 
                    className="w-full btn-neon"
                    onClick={() => handleRent(gpu)}
                    disabled={startingGpu === gpu.id}
                    data-testid={`rent-gpu-${gpu.id}`}
                  >
                    {startingGpu === gpu.id ? (
                      <>جاري التشغيل...</>
                    ) : (
                      <>
                        <Play className="w-4 h-4 mr-2" />
                        استئجار الآن
                      </>
                    )}
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Confirmation Dialog */}
      <Dialog open={confirmDialog} onOpenChange={setConfirmDialog}>
        <DialogContent className="bg-[#12121A] border-[#1E1E2E]">
          <DialogHeader>
            <DialogTitle>تأكيد الاستئجار</DialogTitle>
            <DialogDescription>
              هل أنت متأكد من استئجار {selectedGpu?.name}؟
            </DialogDescription>
          </DialogHeader>
          <div className="py-4 space-y-2">
            <div className="flex justify-between">
              <span className="text-[#8B8B9E]">السعر</span>
              <span className="font-mono text-[#00D4FF]">${selectedGpu?.price_per_hour}/ساعة</span>
            </div>
            <div className="flex justify-between">
              <span className="text-[#8B8B9E]">الحد الأدنى المطلوب</span>
              <span className="font-mono">${selectedGpu?.price_per_hour}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-[#8B8B9E]">رصيدك الحالي</span>
              <span className="font-mono text-[#00FF88]">${user?.balance?.toFixed(2)}</span>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setConfirmDialog(false)}>إلغاء</Button>
            <Button className="btn-neon" onClick={confirmRent} disabled={startingGpu}>
              {startingGpu ? "جاري التشغيل..." : "تأكيد الاستئجار"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

// Instances Page
const InstancesPage = () => {
  const { token, refreshUser } = useAuth();
  const [instances, setInstances] = useState([]);
  const [activeInstances, setActiveInstances] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchActiveInstances, 5000);
    return () => clearInterval(interval);
  }, []);

  const fetchData = async () => {
    try {
      const [allRes, activeRes] = await Promise.all([
        axios.get(`${API}/instances`, { headers: { Authorization: `Bearer ${token}` } }),
        axios.get(`${API}/instances/active`, { headers: { Authorization: `Bearer ${token}` } })
      ]);
      setInstances(allRes.data);
      setActiveInstances(activeRes.data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const fetchActiveInstances = async () => {
    try {
      const res = await axios.get(`${API}/instances/active`, { headers: { Authorization: `Bearer ${token}` } });
      setActiveInstances(res.data);
    } catch (e) {}
  };

  const stopInstance = async (instanceId) => {
    try {
      const res = await axios.post(`${API}/instances/${instanceId}/stop`, {}, { headers: { Authorization: `Bearer ${token}` } });
      toast.success(`تم إيقاف الجلسة. التكلفة: $${res.data.total_cost.toFixed(4)}`);
      fetchData();
      refreshUser();
    } catch (e) {
      toast.error(e.response?.data?.detail || "فشل إيقاف الجلسة");
    }
  };

  if (loading) {
    return <div className="flex items-center justify-center h-64"><div className="spinner"></div></div>;
  }

  return (
    <div className="space-y-6 animate-fade-in" data-testid="instances-page">
      <div>
        <h1 className="text-2xl font-bold">الجلسات</h1>
        <p className="text-[#8B8B9E]">إدارة جلسات GPU الخاصة بك</p>
      </div>

      <Tabs defaultValue="active" className="space-y-6">
        <TabsList className="bg-[#12121A] border border-[#1E1E2E]">
          <TabsTrigger value="active" className="data-[state=active]:bg-[#00D4FF] data-[state=active]:text-[#0A0A0F]">
            نشطة ({activeInstances.length})
          </TabsTrigger>
          <TabsTrigger value="history" className="data-[state=active]:bg-[#00D4FF] data-[state=active]:text-[#0A0A0F]">
            السجل ({instances.length})
          </TabsTrigger>
        </TabsList>

        <TabsContent value="active">
          {activeInstances.length === 0 ? (
            <Card className="gpu-card">
              <CardContent className="p-12 text-center">
                <Activity className="w-16 h-16 mx-auto mb-4 text-[#8B8B9E] opacity-50" />
                <h3 className="text-lg font-semibold mb-2">لا توجد جلسات نشطة</h3>
                <p className="text-[#8B8B9E] mb-4">ابدأ باستئجار GPU من السوق</p>
                <Button className="btn-neon" onClick={() => window.location.href = "/marketplace"}>
                  تصفح GPUs
                </Button>
              </CardContent>
            </Card>
          ) : (
            <div className="space-y-4">
              {activeInstances.map((instance) => (
                <Card key={instance.id} className="gpu-card" data-testid={`instance-${instance.id}`}>
                  <CardContent className="p-6">
                    <div className="flex items-center justify-between mb-4">
                      <div className="flex items-center gap-3">
                        <div className="w-12 h-12 rounded-lg bg-[#00FF88]/10 flex items-center justify-center">
                          <Activity className="w-6 h-6 text-[#00FF88]" />
                        </div>
                        <div>
                          <h3 className="font-semibold text-lg">{instance.gpu_name}</h3>
                          <Badge className="bg-[#00FF88]/10 text-[#00FF88] border-[#00FF88]/30">
                            قيد التشغيل
                          </Badge>
                        </div>
                      </div>
                      <Button 
                        variant="destructive"
                        onClick={() => stopInstance(instance.id)}
                        data-testid={`stop-btn-${instance.id}`}
                      >
                        <Square className="w-4 h-4 mr-2" />
                        إيقاف
                      </Button>
                    </div>

                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
                      <div className="p-3 rounded-lg bg-[#0A0A0F]">
                        <div className="text-[#8B8B9E] text-xs mb-1">المدة</div>
                        <div className="font-mono text-lg">
                          {Math.floor(instance.duration_seconds / 3600)}h {Math.floor((instance.duration_seconds % 3600) / 60)}m {instance.duration_seconds % 60}s
                        </div>
                      </div>
                      <div className="p-3 rounded-lg bg-[#0A0A0F]">
                        <div className="text-[#8B8B9E] text-xs mb-1">التكلفة الحالية</div>
                        <div className="font-mono text-lg text-[#00D4FF]">${instance.current_cost?.toFixed(4)}</div>
                      </div>
                      <div className="p-3 rounded-lg bg-[#0A0A0F]">
                        <div className="text-[#8B8B9E] text-xs mb-1">السعر/ثانية</div>
                        <div className="font-mono text-lg">${instance.price_per_second?.toFixed(6)}</div>
                      </div>
                      <div className="p-3 rounded-lg bg-[#0A0A0F]">
                        <div className="text-[#8B8B9E] text-xs mb-1">بدأ في</div>
                        <div className="font-mono text-sm">{new Date(instance.started_at).toLocaleTimeString('ar')}</div>
                      </div>
                    </div>

                    <div className="p-4 rounded-lg bg-[#0A0A0F] border border-[#1E1E2E]">
                      <h4 className="text-sm font-medium mb-3 text-[#8B8B9E]">بيانات الوصول</h4>
                      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
                        <div>
                          <div className="text-[#8B8B9E] mb-1">SSH</div>
                          <code className="text-[#00D4FF] bg-[#12121A] px-2 py-1 rounded text-xs block truncate">
                            {instance.access_info?.ssh}
                          </code>
                        </div>
                        <div>
                          <div className="text-[#8B8B9E] mb-1">Jupyter</div>
                          <code className="text-[#00D4FF] bg-[#12121A] px-2 py-1 rounded text-xs block truncate">
                            {instance.access_info?.jupyter}
                          </code>
                        </div>
                        <div>
                          <div className="text-[#8B8B9E] mb-1">كلمة المرور</div>
                          <code className="text-[#FFB800] bg-[#12121A] px-2 py-1 rounded text-xs block">
                            {instance.access_info?.password}
                          </code>
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </TabsContent>

        <TabsContent value="history">
          {instances.length === 0 ? (
            <Card className="gpu-card">
              <CardContent className="p-12 text-center">
                <Clock className="w-16 h-16 mx-auto mb-4 text-[#8B8B9E] opacity-50" />
                <h3 className="text-lg font-semibold mb-2">لا يوجد سجل</h3>
                <p className="text-[#8B8B9E]">سيظهر سجل جلساتك هنا</p>
              </CardContent>
            </Card>
          ) : (
            <Card className="gpu-card overflow-hidden">
              <div className="overflow-x-auto">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>GPU</th>
                      <th>الحالة</th>
                      <th>بدأ في</th>
                      <th>انتهى في</th>
                      <th>التكلفة</th>
                    </tr>
                  </thead>
                  <tbody>
                    {instances.map((instance) => (
                      <tr key={instance.id}>
                        <td className="font-medium">{instance.gpu_name}</td>
                        <td>
                          <Badge className={instance.status === "running" ? "bg-[#00FF88]/10 text-[#00FF88]" : "bg-[#8B8B9E]/10 text-[#8B8B9E]"}>
                            {instance.status === "running" ? "نشط" : "منتهي"}
                          </Badge>
                        </td>
                        <td className="font-mono text-sm">{new Date(instance.started_at).toLocaleString('ar')}</td>
                        <td className="font-mono text-sm">{instance.stopped_at ? new Date(instance.stopped_at).toLocaleString('ar') : "-"}</td>
                        <td className="font-mono text-[#00D4FF]">${instance.total_cost?.toFixed(4) || "0.0000"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
};

// Billing Page
const BillingPage = () => {
  const { user, token, refreshUser } = useAuth();
  const [searchParams] = useSearchParams();
  const [transactions, setTransactions] = useState([]);
  const [invoices, setInvoices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [addFundsOpen, setAddFundsOpen] = useState(false);
  const [amount, setAmount] = useState("50");
  const [processing, setProcessing] = useState(false);

  useEffect(() => {
    fetchData();
    checkPaymentStatus();
  }, []);

  const fetchData = async () => {
    try {
      const [transRes, invoiceRes] = await Promise.all([
        axios.get(`${API}/billing/transactions`, { headers: { Authorization: `Bearer ${token}` } }),
        axios.get(`${API}/billing/invoices`, { headers: { Authorization: `Bearer ${token}` } })
      ]);
      setTransactions(transRes.data);
      setInvoices(invoiceRes.data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const checkPaymentStatus = async () => {
    const sessionId = searchParams.get("session_id");
    if (sessionId) {
      try {
        const res = await axios.get(`${API}/payments/status/${sessionId}`, { headers: { Authorization: `Bearer ${token}` } });
        if (res.data.payment_status === "paid") {
          toast.success(`تم إضافة $${res.data.amount} إلى رصيدك`);
          refreshUser();
          fetchData();
        }
      } catch (e) {
        console.error(e);
      }
      // Clear the URL parameter
      window.history.replaceState({}, "", "/billing");
    }
  };

  const handleAddFunds = async () => {
    const amountNum = parseFloat(amount);
    if (amountNum < 5) {
      toast.error("الحد الأدنى $5");
      return;
    }
    setProcessing(true);
    try {
      const res = await axios.post(`${API}/payments/create-checkout`, {
        amount: amountNum,
        origin_url: window.location.origin
      }, { headers: { Authorization: `Bearer ${token}` } });
      window.location.href = res.data.url;
    } catch (e) {
      toast.error(e.response?.data?.detail || "فشل إنشاء جلسة الدفع");
      setProcessing(false);
    }
  };

  if (loading) {
    return <div className="flex items-center justify-center h-64"><div className="spinner"></div></div>;
  }

  return (
    <div className="space-y-6 animate-fade-in" data-testid="billing-page">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">الفوترة</h1>
          <p className="text-[#8B8B9E]">إدارة رصيدك والمعاملات</p>
        </div>
        <Button className="btn-neon" onClick={() => setAddFundsOpen(true)} data-testid="add-funds-dialog-btn">
          <Plus className="w-4 h-4 mr-2" />
          إضافة رصيد
        </Button>
      </div>

      {/* Balance Card */}
      <Card className="gpu-card neon-border">
        <CardContent className="p-8">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-[#8B8B9E] mb-2">رصيدك الحالي</p>
              <p className="text-5xl font-bold text-[#00D4FF]" data-testid="current-balance">
                ${user?.balance?.toFixed(2)}
              </p>
            </div>
            <div className="w-20 h-20 rounded-full bg-[#00D4FF]/10 flex items-center justify-center">
              <Wallet className="w-10 h-10 text-[#00D4FF]" />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Quick Add */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[10, 25, 50, 100].map((val) => (
          <Button
            key={val}
            variant="outline"
            className="h-16 text-lg btn-outline"
            onClick={() => { setAmount(val.toString()); setAddFundsOpen(true); }}
            data-testid={`quick-add-${val}`}
          >
            <Plus className="w-4 h-4 mr-2" />
            ${val}
          </Button>
        ))}
      </div>

      <Tabs defaultValue="transactions" className="space-y-6">
        <TabsList className="bg-[#12121A] border border-[#1E1E2E]">
          <TabsTrigger value="transactions" className="data-[state=active]:bg-[#00D4FF] data-[state=active]:text-[#0A0A0F]">
            المعاملات
          </TabsTrigger>
          <TabsTrigger value="invoices" className="data-[state=active]:bg-[#00D4FF] data-[state=active]:text-[#0A0A0F]">
            الفواتير
          </TabsTrigger>
        </TabsList>

        <TabsContent value="transactions">
          {transactions.length === 0 ? (
            <Card className="gpu-card">
              <CardContent className="p-12 text-center">
                <CreditCard className="w-16 h-16 mx-auto mb-4 text-[#8B8B9E] opacity-50" />
                <h3 className="text-lg font-semibold mb-2">لا توجد معاملات</h3>
                <p className="text-[#8B8B9E]">ستظهر معاملاتك هنا</p>
              </CardContent>
            </Card>
          ) : (
            <Card className="gpu-card overflow-hidden">
              <div className="overflow-x-auto">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>النوع</th>
                      <th>الوصف</th>
                      <th>المبلغ</th>
                      <th>التاريخ</th>
                    </tr>
                  </thead>
                  <tbody>
                    {transactions.map((t) => (
                      <tr key={t.id}>
                        <td>
                          <Badge className={t.type === "deposit" ? "bg-[#00FF88]/10 text-[#00FF88]" : "bg-[#FF4757]/10 text-[#FF4757]"}>
                            {t.type === "deposit" ? "إيداع" : "استخدام"}
                          </Badge>
                        </td>
                        <td>{t.description}</td>
                        <td className={`font-mono ${t.amount >= 0 ? "text-[#00FF88]" : "text-[#FF4757]"}`}>
                          {t.amount >= 0 ? "+" : ""}{t.amount.toFixed(4)}$
                        </td>
                        <td className="font-mono text-sm">{new Date(t.created_at).toLocaleString('ar')}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="invoices">
          {invoices.length === 0 ? (
            <Card className="gpu-card">
              <CardContent className="p-12 text-center">
                <FileText className="w-16 h-16 mx-auto mb-4 text-[#8B8B9E] opacity-50" />
                <h3 className="text-lg font-semibold mb-2">لا توجد فواتير</h3>
                <p className="text-[#8B8B9E]">ستظهر فواتيرك هنا بعد استخدام GPU</p>
              </CardContent>
            </Card>
          ) : (
            <Card className="gpu-card overflow-hidden">
              <div className="overflow-x-auto">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>GPU</th>
                      <th>المدة</th>
                      <th>التكلفة</th>
                      <th>التاريخ</th>
                    </tr>
                  </thead>
                  <tbody>
                    {invoices.map((inv) => (
                      <tr key={inv.id}>
                        <td className="font-medium">{inv.gpu_name}</td>
                        <td className="font-mono">{Math.floor(inv.duration_seconds / 60)}m {inv.duration_seconds % 60}s</td>
                        <td className="font-mono text-[#00D4FF]">${inv.total_cost.toFixed(4)}</td>
                        <td className="font-mono text-sm">{new Date(inv.created_at).toLocaleString('ar')}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          )}
        </TabsContent>
      </Tabs>

      {/* Add Funds Dialog */}
      <Dialog open={addFundsOpen} onOpenChange={setAddFundsOpen}>
        <DialogContent className="bg-[#12121A] border-[#1E1E2E]">
          <DialogHeader>
            <DialogTitle>إضافة رصيد</DialogTitle>
            <DialogDescription>أدخل المبلغ الذي تريد إضافته (الحد الأدنى $5)</DialogDescription>
          </DialogHeader>
          <div className="py-4">
            <Label htmlFor="amount" className="mb-2 block">المبلغ ($)</Label>
            <Input
              id="amount"
              type="number"
              min="5"
              step="1"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              className="text-2xl font-mono text-center"
              data-testid="add-funds-amount-input"
            />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setAddFundsOpen(false)}>إلغاء</Button>
            <Button className="btn-neon" onClick={handleAddFunds} disabled={processing} data-testid="confirm-add-funds-btn">
              {processing ? "جاري المعالجة..." : `إضافة $${amount}`}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

// ============== SECURITY PAGE - 2FA ==============
const SecurityPage = () => {
  const { token, user } = useAuth();
  const [loading, setLoading] = useState(true);
  const [twoFAStatus, setTwoFAStatus] = useState({ enabled: false, method: null });
  const [setupMode, setSetupMode] = useState(false);
  const [selectedMethod, setSelectedMethod] = useState("both");
  const [qrCode, setQrCode] = useState(null);
  const [manualKey, setManualKey] = useState(null);
  const [verificationCode, setVerificationCode] = useState("");
  const [verifying, setVerifying] = useState(false);
  const [disableMode, setDisableMode] = useState(false);
  const [disableCode, setDisableCode] = useState("");

  useEffect(() => {
    fetchStatus();
  }, []);

  const fetchStatus = async () => {
    try {
      const res = await axios.get(`${API}/auth/2fa/status`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setTwoFAStatus(res.data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const startSetup = async () => {
    try {
      setLoading(true);
      const res = await axios.post(`${API}/auth/2fa/setup`, 
        { method: selectedMethod },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setQrCode(res.data.qr_code);
      setManualKey(res.data.manual_key);
      setSetupMode(true);
      if (res.data.email_sent) {
        toast.success("تم إرسال رمز التحقق إلى بريدك");
      }
    } catch (e) {
      toast.error("فشل بدء الإعداد");
    } finally {
      setLoading(false);
    }
  };

  const verifySetup = async () => {
    if (verificationCode.length !== 6) {
      toast.error("أدخل رمز من 6 أرقام");
      return;
    }
    
    setVerifying(true);
    try {
      await axios.post(`${API}/auth/2fa/verify-setup`,
        { code: verificationCode, method: selectedMethod === "email" ? "email" : "totp" },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.success("تم تفعيل المصادقة الثنائية بنجاح! 🎉");
      setSetupMode(false);
      setQrCode(null);
      setManualKey(null);
      setVerificationCode("");
      fetchStatus();
    } catch (e) {
      toast.error(e.response?.data?.detail || "رمز غير صحيح");
    } finally {
      setVerifying(false);
    }
  };

  const disable2FA = async () => {
    if (disableCode.length !== 6) {
      toast.error("أدخل رمز من 6 أرقام");
      return;
    }
    
    setVerifying(true);
    try {
      await axios.post(`${API}/auth/2fa/disable`,
        { code: disableCode, method: "totp" },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.success("تم إلغاء المصادقة الثنائية");
      setDisableMode(false);
      setDisableCode("");
      fetchStatus();
    } catch (e) {
      toast.error(e.response?.data?.detail || "رمز غير صحيح");
    } finally {
      setVerifying(false);
    }
  };

  const sendEmailCode = async () => {
    try {
      await axios.post(`${API}/auth/2fa/send-email-code`, {}, {
        headers: { Authorization: `Bearer ${token}` }
      });
      toast.success("تم إرسال رمز جديد إلى بريدك");
    } catch (e) {
      toast.error("فشل إرسال الرمز");
    }
  };

  if (loading) {
    return <div className="flex items-center justify-center h-64"><div className="spinner"></div></div>;
  }

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <h1 className="text-2xl font-bold">الأمان</h1>
        <p className="text-[#8B8B9E]">إدارة إعدادات الأمان وحماية حسابك</p>
      </div>

      {/* حالة 2FA الحالية */}
      <Card className="gpu-card">
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className={`w-12 h-12 rounded-lg flex items-center justify-center ${
                twoFAStatus.enabled ? 'bg-[#00FF88]/10' : 'bg-[#8B8B9E]/10'
              }`}>
                <Shield className={`w-6 h-6 ${twoFAStatus.enabled ? 'text-[#00FF88]' : 'text-[#8B8B9E]'}`} />
              </div>
              <div>
                <CardTitle>المصادقة الثنائية (2FA)</CardTitle>
                <CardDescription>
                  {twoFAStatus.enabled ? (
                    <span className="text-[#00FF88]">مفعّلة - {twoFAStatus.method === 'both' ? 'تطبيق + بريد' : twoFAStatus.method === 'totp' ? 'تطبيق' : 'بريد'}</span>
                  ) : (
                    <span className="text-[#FFB800]">غير مفعّلة - حسابك أقل حماية</span>
                  )}
                </CardDescription>
              </div>
            </div>
            <Badge className={twoFAStatus.enabled ? 'bg-[#00FF88]/10 text-[#00FF88]' : 'bg-[#FFB800]/10 text-[#FFB800]'}>
              {twoFAStatus.enabled ? 'مفعّلة' : 'غير مفعّلة'}
            </Badge>
          </div>
        </CardHeader>
        <CardContent>
          {!setupMode && !disableMode && (
            <>
              <p className="text-[#8B8B9E] mb-4">
                المصادقة الثنائية تضيف طبقة حماية إضافية لحسابك. عند تفعيلها، ستحتاج إلى رمز إضافي عند تسجيل الدخول.
              </p>
              
              {!twoFAStatus.enabled ? (
                <div className="space-y-4">
                  <div className="p-4 rounded-lg bg-[#0A0A0F] border border-[#1E1E2E]">
                    <Label className="mb-3 block">اختر طريقة المصادقة</Label>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                      <div
                        className={`p-4 rounded-lg border cursor-pointer transition-all ${
                          selectedMethod === 'totp' ? 'border-[#00D4FF] bg-[#00D4FF]/5' : 'border-[#1E1E2E] hover:border-[#00D4FF]/50'
                        }`}
                        onClick={() => setSelectedMethod('totp')}
                      >
                        <Smartphone className="w-8 h-8 text-[#00D4FF] mb-2" />
                        <h4 className="font-medium">تطبيق المصادقة</h4>
                        <p className="text-xs text-[#8B8B9E] mt-1">Google Authenticator أو Authy</p>
                      </div>
                      <div
                        className={`p-4 rounded-lg border cursor-pointer transition-all ${
                          selectedMethod === 'email' ? 'border-[#00D4FF] bg-[#00D4FF]/5' : 'border-[#1E1E2E] hover:border-[#00D4FF]/50'
                        }`}
                        onClick={() => setSelectedMethod('email')}
                      >
                        <Mail className="w-8 h-8 text-[#FFB800] mb-2" />
                        <h4 className="font-medium">البريد الإلكتروني</h4>
                        <p className="text-xs text-[#8B8B9E] mt-1">رمز يصل لبريدك</p>
                      </div>
                      <div
                        className={`p-4 rounded-lg border cursor-pointer transition-all ${
                          selectedMethod === 'both' ? 'border-[#00D4FF] bg-[#00D4FF]/5' : 'border-[#1E1E2E] hover:border-[#00D4FF]/50'
                        }`}
                        onClick={() => setSelectedMethod('both')}
                      >
                        <Shield className="w-8 h-8 text-[#00FF88] mb-2" />
                        <h4 className="font-medium">كلاهما (موصى به)</h4>
                        <p className="text-xs text-[#8B8B9E] mt-1">أقصى حماية</p>
                      </div>
                    </div>
                  </div>
                  <Button className="btn-neon" onClick={startSetup}>
                    <Shield className="w-4 h-4 mr-2" />
                    تفعيل المصادقة الثنائية
                  </Button>
                </div>
              ) : (
                <Button variant="destructive" onClick={() => setDisableMode(true)}>
                  إلغاء المصادقة الثنائية
                </Button>
              )}
            </>
          )}

          {/* وضع الإعداد */}
          {setupMode && (
            <div className="space-y-6">
              {(selectedMethod === 'totp' || selectedMethod === 'both') && qrCode && (
                <div className="text-center">
                  <h3 className="font-medium mb-4">1. امسح رمز QR بتطبيق المصادقة</h3>
                  <div className="inline-block p-4 bg-white rounded-lg mb-4">
                    <img src={qrCode} alt="QR Code" className="w-48 h-48" />
                  </div>
                  {manualKey && (
                    <div className="p-3 rounded-lg bg-[#0A0A0F] border border-[#1E1E2E]">
                      <p className="text-xs text-[#8B8B9E] mb-1">أو أدخل الرمز يدوياً:</p>
                      <div className="flex items-center justify-center gap-2">
                        <code className="font-mono text-[#00D4FF]">{manualKey}</code>
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => {
                            navigator.clipboard.writeText(manualKey);
                            toast.success("تم النسخ!");
                          }}
                        >
                          <Copy className="w-4 h-4" />
                        </Button>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {selectedMethod === 'email' && (
                <div className="text-center">
                  <h3 className="font-medium mb-4">تم إرسال رمز إلى بريدك</h3>
                  <p className="text-[#8B8B9E] mb-4">{user?.email}</p>
                  <Button variant="outline" onClick={sendEmailCode}>
                    <Mail className="w-4 h-4 mr-2" />
                    إرسال رمز جديد
                  </Button>
                </div>
              )}

              <div className="space-y-3">
                <h3 className="font-medium text-center">
                  {selectedMethod === 'both' ? '2. أدخل الرمز من التطبيق' : 'أدخل الرمز'}
                </h3>
                <Input
                  type="text"
                  placeholder="000000"
                  value={verificationCode}
                  onChange={(e) => setVerificationCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                  className="text-center text-2xl font-mono tracking-widest max-w-xs mx-auto"
                  maxLength={6}
                />
              </div>

              <div className="flex gap-3 justify-center">
                <Button variant="outline" onClick={() => { setSetupMode(false); setQrCode(null); }}>
                  إلغاء
                </Button>
                <Button 
                  className="btn-neon" 
                  onClick={verifySetup}
                  disabled={verifying || verificationCode.length !== 6}
                >
                  {verifying ? "جاري التحقق..." : "تأكيد التفعيل"}
                </Button>
              </div>
            </div>
          )}

          {/* وضع الإلغاء */}
          {disableMode && (
            <div className="space-y-4">
              <div className="p-4 rounded-lg bg-[#FF4757]/10 border border-[#FF4757]/30">
                <p className="text-[#FF4757] text-sm">
                  تحذير: إلغاء المصادقة الثنائية سيجعل حسابك أقل أماناً
                </p>
              </div>
              <div className="space-y-2">
                <Label>أدخل رمز المصادقة للتأكيد</Label>
                <Input
                  type="text"
                  placeholder="000000"
                  value={disableCode}
                  onChange={(e) => setDisableCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                  className="text-center text-xl font-mono tracking-widest max-w-xs"
                  maxLength={6}
                />
              </div>
              <div className="flex gap-3">
                <Button variant="outline" onClick={() => { setDisableMode(false); setDisableCode(""); }}>
                  رجوع
                </Button>
                <Button 
                  variant="destructive" 
                  onClick={disable2FA}
                  disabled={verifying || disableCode.length !== 6}
                >
                  {verifying ? "جاري..." : "تأكيد الإلغاء"}
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* معلومات الأمان */}
      <Card className="gpu-card">
        <CardHeader>
          <CardTitle className="text-lg">نصائح أمنية</CardTitle>
        </CardHeader>
        <CardContent>
          <ul className="space-y-3 text-[#8B8B9E]">
            <li className="flex items-start gap-2">
              <Check className="w-5 h-5 text-[#00FF88] mt-0.5" />
              <span>استخدم كلمة مرور قوية وفريدة لهذا الحساب</span>
            </li>
            <li className="flex items-start gap-2">
              <Check className="w-5 h-5 text-[#00FF88] mt-0.5" />
              <span>فعّل المصادقة الثنائية لحماية إضافية</span>
            </li>
            <li className="flex items-start gap-2">
              <Check className="w-5 h-5 text-[#00FF88] mt-0.5" />
              <span>لا تشارك بيانات حسابك مع أحد</span>
            </li>
            <li className="flex items-start gap-2">
              <Check className="w-5 h-5 text-[#00FF88] mt-0.5" />
              <span>راجع سجل النشاط بانتظام</span>
            </li>
          </ul>
        </CardContent>
      </Card>
    </div>
  );
};

// ============== PROVIDER DASHBOARD ==============
const ProviderLoginPage = () => {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const res = await axios.post(`${API}/provider/login`, { email, password });
      localStorage.setItem("provider_token", res.data.token);
      toast.success("تم تسجيل الدخول بنجاح");
      navigate("/provider/dashboard");
    } catch (err) {
      toast.error(err.response?.data?.detail || "فشل تسجيل الدخول");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen gradient-mesh flex items-center justify-center px-4">
      <Card className="w-full max-w-md gpu-card">
        <CardHeader className="text-center">
          <div className="w-12 h-12 rounded-lg bg-gradient-to-br from-[#00FF88] to-[#00CC6A] flex items-center justify-center mx-auto mb-4">
            <Server className="w-6 h-6 text-[#0A0A0F]" />
          </div>
          <CardTitle className="text-2xl">لوحة المزودين</CardTitle>
          <CardDescription>سجل دخول لإدارة كروتك</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label>البريد الإلكتروني</Label>
              <Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
            </div>
            <div className="space-y-2">
              <Label>كلمة المرور</Label>
              <Input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
            </div>
            <Button type="submit" className="w-full bg-[#00FF88] hover:bg-[#00CC6A] text-black" disabled={loading}>
              {loading ? "جاري التحميل..." : "دخول"}
            </Button>
          </form>
          <div className="mt-4 text-center text-sm text-[#8B8B9E]">
            بيانات التجربة: provider@gpucloud.pro / demo123
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

const ProviderDashboard = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [addGPUOpen, setAddGPUOpen] = useState(false);
  const [feedbackOpen, setFeedbackOpen] = useState(false);
  const [detecting, setDetecting] = useState(false);
  const [gpuForm, setGpuForm] = useState({
    name: '',
    model: '',
    vram: '',
    price_per_hour: '',
    region: ''
  });
  const [feedbackText, setFeedbackText] = useState('');
  const [sendingFeedback, setSendingFeedback] = useState(false);
  const navigate = useNavigate();
  const token = localStorage.getItem("provider_token");

  useEffect(() => {
    if (!token) {
      navigate("/provider/login");
      return;
    }
    fetchData();
  }, [token]);

  const fetchData = async () => {
    try {
      const res = await axios.get(`${API}/provider/dashboard`, { headers: { Authorization: `Bearer ${token}` } });
      setData(res.data);
    } catch (e) {
      toast.error("فشل تحميل البيانات");
      navigate("/provider/login");
    } finally {
      setLoading(false);
    }
  };

  // اكتشاف GPU تلقائي عبر WebGL
  const detectGPU = async () => {
    setDetecting(true);
    try {
      const canvas = document.createElement('canvas');
      const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
      
      if (gl) {
        const debugInfo = gl.getExtension('WEBGL_debug_renderer_info');
        let renderer = 'Unknown GPU';
        
        if (debugInfo) {
          renderer = gl.getParameter(debugInfo.UNMASKED_RENDERER_WEBGL);
        }
        
        // تحليل اسم الكرت
        let gpuName = renderer;
        let vram = '8';
        let model = '';
        
        // اكتشاف نوع الكرت
        if (renderer.includes('RTX 4090')) {
          gpuName = 'NVIDIA RTX 4090';
          vram = '24';
          model = 'RTX 4090';
        } else if (renderer.includes('RTX 4080')) {
          gpuName = 'NVIDIA RTX 4080';
          vram = '16';
          model = 'RTX 4080';
        } else if (renderer.includes('RTX 4070')) {
          gpuName = 'NVIDIA RTX 4070';
          vram = '12';
          model = 'RTX 4070';
        } else if (renderer.includes('RTX 3090')) {
          gpuName = 'NVIDIA RTX 3090';
          vram = '24';
          model = 'RTX 3090';
        } else if (renderer.includes('RTX 3080')) {
          gpuName = 'NVIDIA RTX 3080';
          vram = '10';
          model = 'RTX 3080';
        } else if (renderer.includes('A100')) {
          gpuName = 'NVIDIA A100';
          vram = '80';
          model = 'A100';
        } else if (renderer.includes('H100')) {
          gpuName = 'NVIDIA H100';
          vram = '80';
          model = 'H100';
        } else if (renderer.includes('AMD') || renderer.includes('Radeon')) {
          gpuName = renderer;
          model = 'AMD';
        }
        
        setGpuForm(prev => ({
          ...prev,
          name: gpuName,
          model: model || gpuName.split(' ').pop(),
          vram: vram
        }));
        
        toast.success(`تم اكتشاف: ${gpuName}`);
      } else {
        toast.error("لم نتمكن من اكتشاف GPU - أدخل البيانات يدوياً");
      }
    } catch (e) {
      toast.error("فشل الاكتشاف التلقائي");
    } finally {
      setDetecting(false);
    }
  };

  const addGPU = async () => {
    if (!gpuForm.name || !gpuForm.price_per_hour) {
      toast.error("أدخل اسم الكرت والسعر");
      return;
    }
    
    try {
      await axios.post(`${API}/provider/gpu/add`, gpuForm, {
        headers: { Authorization: `Bearer ${token}` }
      });
      toast.success("تم إضافة الكرت بنجاح! 🎉");
      setAddGPUOpen(false);
      setGpuForm({ name: '', model: '', vram: '', price_per_hour: '', region: '' });
      fetchData();
    } catch (e) {
      toast.error(e.response?.data?.detail || "فشل إضافة الكرت");
    }
  };

  const sendFeedback = async () => {
    if (!feedbackText.trim()) {
      toast.error("اكتب ملاحظتك");
      return;
    }
    
    setSendingFeedback(true);
    try {
      await axios.post(`${API}/feedback`, {
        message: feedbackText,
        type: 'provider'
      }, {
        headers: { Authorization: `Bearer ${token}` }
      });
      toast.success("تم إرسال ملاحظتك للإدارة ✅");
      setFeedbackOpen(false);
      setFeedbackText('');
    } catch (e) {
      toast.error("فشل الإرسال");
    } finally {
      setSendingFeedback(false);
    }
  };

  if (loading) return <div className="min-h-screen flex items-center justify-center bg-[#0A0A0F]"><div className="spinner"></div></div>;

  return (
    <div className="min-h-screen bg-[#0A0A0F] p-6">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-lg bg-gradient-to-br from-[#00FF88] to-[#00CC6A] flex items-center justify-center">
              <Server className="w-6 h-6 text-[#0A0A0F]" />
            </div>
            <div>
              <h1 className="text-2xl font-bold">{data?.provider?.company_name}</h1>
              <p className="text-[#8B8B9E]">لوحة تحكم المزود</p>
            </div>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => setFeedbackOpen(true)}>
              <MessageSquare className="w-4 h-4 mr-2" /> ملاحظات
            </Button>
            <Button variant="outline" onClick={() => { localStorage.removeItem("provider_token"); navigate("/"); }}>
              <LogOut className="w-4 h-4 mr-2" /> خروج
            </Button>
          </div>
        </div>

        {/* Quick Actions */}
        <Card className="gpu-card neon-border">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-lg font-semibold mb-2">أضف كرت GPU جديد</h3>
                <p className="text-[#8B8B9E]">سجل كرتك وابدأ بتحقيق الأرباح</p>
              </div>
              <Button className="btn-neon" onClick={() => setAddGPUOpen(true)}>
                <Plus className="w-4 h-4 mr-2" /> إضافة GPU
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Stats */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card className="gpu-card">
            <CardContent className="p-6">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 rounded-lg bg-[#00FF88]/10 flex items-center justify-center">
                  <DollarSign className="w-6 h-6 text-[#00FF88]" />
                </div>
                <div>
                  <p className="text-[#8B8B9E] text-sm">إجمالي الأرباح</p>
                  <p className="text-2xl font-bold text-[#00FF88]">${data?.earnings?.total?.toFixed(2)}</p>
                </div>
              </div>
            </CardContent>
          </Card>
          <Card className="gpu-card">
            <CardContent className="p-6">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 rounded-lg bg-[#00D4FF]/10 flex items-center justify-center">
                  <Wallet className="w-6 h-6 text-[#00D4FF]" />
                </div>
                <div>
                  <p className="text-[#8B8B9E] text-sm">رصيد قابل للسحب</p>
                  <p className="text-2xl font-bold text-[#00D4FF]">${data?.earnings?.pending_payout?.toFixed(4)}</p>
                </div>
              </div>
            </CardContent>
          </Card>
          <Card className="gpu-card">
            <CardContent className="p-6">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 rounded-lg bg-[#FFB800]/10 flex items-center justify-center">
                  <Server className="w-6 h-6 text-[#FFB800]" />
                </div>
                <div>
                  <p className="text-[#8B8B9E] text-sm">إجمالي GPUs</p>
                  <p className="text-2xl font-bold">{data?.total_gpus}</p>
                </div>
              </div>
            </CardContent>
          </Card>
          <Card className="gpu-card">
            <CardContent className="p-6">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 rounded-lg bg-[#FF4757]/10 flex items-center justify-center">
                  <Activity className="w-6 h-6 text-[#FF4757]" />
                </div>
                <div>
                  <p className="text-[#8B8B9E] text-sm">كروت نشطة</p>
                  <p className="text-2xl font-bold">{data?.active_gpus}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Revenue Info */}
        <Card className="gpu-card">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-lg font-semibold mb-2">توزيع الأرباح</h3>
                <p className="text-[#8B8B9E]">تحصل على <span className="text-[#00FF88] font-bold">85%</span> من كل معاملة</p>
                <p className="text-[#8B8B9E] text-sm">عمولة المنصة: {data?.earnings?.platform_fee_percent}%</p>
              </div>
              <div className="text-right">
                <p className="text-sm text-[#8B8B9E]">أرباح اليوم</p>
                <p className="text-3xl font-bold text-[#00FF88]">${data?.earnings?.today?.toFixed(4)}</p>
              </div>
            </div>
          </CardContent>
        </Card>
            </div>
          </CardContent>
        </Card>

        {/* GPUs List */}
        <Card className="gpu-card">
          <CardHeader>
            <CardTitle>كروتك المسجلة</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {data?.gpus?.map((gpu) => (
                <div key={gpu.id} className="p-4 rounded-lg bg-[#0A0A0F] border border-[#1E1E2E] flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <div className={`status-dot ${gpu.status === 'available' ? 'available' : gpu.status === 'in_use' ? 'in-use' : 'offline'}`}></div>
                    <div>
                      <p className="font-semibold">{gpu.name}</p>
                      <p className="text-sm text-[#8B8B9E]">{gpu.region} • {gpu.vram}GB VRAM</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="font-mono text-[#00D4FF]">${gpu.price_per_hour}/hr</p>
                    <Badge className={gpu.status === 'available' ? 'bg-[#00FF88]/10 text-[#00FF88]' : gpu.status === 'in_use' ? 'bg-[#FFB800]/10 text-[#FFB800]' : 'bg-[#8B8B9E]/10 text-[#8B8B9E]'}>
                      {gpu.status === 'available' ? 'متاح' : gpu.status === 'in_use' ? 'مستأجر' : 'صيانة'}
                    </Badge>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Recent Transactions */}
        <Card className="gpu-card">
          <CardHeader>
            <CardTitle>آخر المعاملات</CardTitle>
          </CardHeader>
          <CardContent>
            {data?.recent_transactions?.length === 0 ? (
              <p className="text-center text-[#8B8B9E] py-8">لا توجد معاملات بعد</p>
            ) : (
              <div className="space-y-2">
                {data?.recent_transactions?.map((t) => (
                  <div key={t.id} className="flex items-center justify-between p-3 rounded-lg bg-[#0A0A0F]">
                    <div>
                      <p className="text-sm">{t.gpu_name}</p>
                      <p className="text-xs text-[#8B8B9E]">{new Date(t.created_at).toLocaleString('ar')}</p>
                    </div>
                    <div className="text-right">
                      <p className="text-[#00FF88] font-mono">+${t.net_amount?.toFixed(4)}</p>
                      <p className="text-xs text-[#8B8B9E]">من ${t.gross_amount?.toFixed(4)}</p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

// ============== ADMIN DASHBOARD ==============
const AdminDashboard = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();
  const token = localStorage.getItem("token");

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const res = await axios.get(`${API}/admin/stats`, { headers: { Authorization: `Bearer ${token}` } });
      setData(res.data);
    } catch (e) {
      toast.error("غير مصرح - تحتاج صلاحيات الأدمن");
      navigate("/dashboard");
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <div className="flex items-center justify-center h-64"><div className="spinner"></div></div>;

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <h1 className="text-2xl font-bold">لوحة الإدارة</h1>
        <p className="text-[#8B8B9E]">إحصائيات المنصة والإيرادات</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card className="gpu-card">
          <CardContent className="p-6">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 rounded-lg bg-[#00D4FF]/10 flex items-center justify-center">
                <Users className="w-6 h-6 text-[#00D4FF]" />
              </div>
              <div>
                <p className="text-[#8B8B9E] text-sm">المستخدمين</p>
                <p className="text-2xl font-bold">{data?.total_users}</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="gpu-card">
          <CardContent className="p-6">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 rounded-lg bg-[#00FF88]/10 flex items-center justify-center">
                <Server className="w-6 h-6 text-[#00FF88]" />
              </div>
              <div>
                <p className="text-[#8B8B9E] text-sm">المزودين</p>
                <p className="text-2xl font-bold">{data?.total_providers}</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="gpu-card">
          <CardContent className="p-6">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 rounded-lg bg-[#FFB800]/10 flex items-center justify-center">
                <Cpu className="w-6 h-6 text-[#FFB800]" />
              </div>
              <div>
                <p className="text-[#8B8B9E] text-sm">GPUs</p>
                <p className="text-2xl font-bold">{data?.total_gpus}</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="gpu-card">
          <CardContent className="p-6">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 rounded-lg bg-[#FF4757]/10 flex items-center justify-center">
                <Activity className="w-6 h-6 text-[#FF4757]" />
              </div>
              <div>
                <p className="text-[#8B8B9E] text-sm">جلسات نشطة</p>
                <p className="text-2xl font-bold">{data?.active_instances}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Revenue */}
      <Card className="gpu-card neon-border">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <DollarSign className="w-5 h-5 text-[#00FF88]" />
            إيرادات المنصة
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="p-4 rounded-lg bg-[#0A0A0F]">
              <p className="text-[#8B8B9E] text-sm mb-1">إجمالي المعاملات</p>
              <p className="text-2xl font-bold">${data?.revenue?.total_transactions?.toFixed(4)}</p>
            </div>
            <div className="p-4 rounded-lg bg-[#0A0A0F]">
              <p className="text-[#8B8B9E] text-sm mb-1">عمولة المنصة ({data?.revenue?.fee_percent}%)</p>
              <p className="text-2xl font-bold text-[#00FF88]">${data?.revenue?.platform_fees?.toFixed(4)}</p>
            </div>
            <div className="p-4 rounded-lg bg-[#0A0A0F]">
              <p className="text-[#8B8B9E] text-sm mb-1">حصة المزودين (85%)</p>
              <p className="text-2xl font-bold text-[#00D4FF]">${data?.revenue?.provider_share?.toFixed(4)}</p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

// Main App
function App() {
  useEffect(() => {
    // Seed data on first load
    axios.post(`${API}/seed`).catch(() => {});
  }, []);

  return (
    <AuthProvider>
      <BrowserRouter>
        <Toaster position="top-center" richColors theme="dark" />
        <AppRoutes />
      </BrowserRouter>
    </AuthProvider>
  );
}

// App Routes with Auth Callback handling
const AppRoutes = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { setAuthFromGoogle } = useAuth();
  const processedRef = React.useRef(false);

  useEffect(() => {
    // معالجة session_id من Google Auth
    const hash = location.hash;
    if (hash && hash.includes('session_id=') && !processedRef.current) {
      processedRef.current = true;
      const sessionId = hash.split('session_id=')[1]?.split('&')[0];
      
      if (sessionId) {
        // جلب بيانات المستخدم
        fetch('https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data', {
          headers: { 'X-Session-ID': sessionId }
        })
        .then(res => res.json())
        .then(async (data) => {
          // حفظ المستخدم في قاعدة البيانات
          const backendRes = await axios.post(`${API}/auth/google`, {
            email: data.email,
            name: data.name,
            picture: data.picture,
            google_id: data.id
          });
          
          setAuthFromGoogle(backendRes.data.user, backendRes.data.token);
          toast.success(`مرحباً ${data.name}! 🎉`);
          window.history.replaceState({}, '', '/dashboard');
          navigate('/dashboard', { replace: true });
        })
        .catch((err) => {
          console.error('Google auth error:', err);
          toast.error("فشل تسجيل الدخول");
          navigate('/login');
        });
      }
    }
  }, [location.hash]);

  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route path="/provider/login" element={<ProviderLoginPage />} />
      <Route path="/provider/dashboard" element={<ProviderDashboard />} />
      <Route path="/dashboard" element={
        <ProtectedRoute>
          <DashboardLayout><DashboardHome /></DashboardLayout>
        </ProtectedRoute>
      } />
      <Route path="/marketplace" element={
        <ProtectedRoute>
          <DashboardLayout><MarketplacePage /></DashboardLayout>
        </ProtectedRoute>
      } />
      <Route path="/instances" element={
        <ProtectedRoute>
          <DashboardLayout><InstancesPage /></DashboardLayout>
        </ProtectedRoute>
      } />
      <Route path="/billing" element={
        <ProtectedRoute>
          <DashboardLayout><BillingPage /></DashboardLayout>
        </ProtectedRoute>
      } />
      <Route path="/security" element={
        <ProtectedRoute>
          <DashboardLayout><SecurityPage /></DashboardLayout>
        </ProtectedRoute>
      } />
      <Route path="/admin" element={
        <ProtectedRoute>
          <DashboardLayout><AdminDashboard /></DashboardLayout>
        </ProtectedRoute>
      } />
    </Routes>
  );
}

export default App;
