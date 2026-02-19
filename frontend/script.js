const IS_LOCAL = window.location.hostname === 'localhost' ||
                 window.location.hostname === '127.0.0.1' ||
                 window.location.protocol === 'file:';

  const API_BASE = IS_LOCAL
  ? 'http://127.0.0.1:5000'
  : 'https://titanic-l2cj.onrender.com' ;
  
console.log('API_BASE:', API_BASE);

function getToken()    { return localStorage.getItem('ts_token'); }
function setToken(t)   { localStorage.setItem('ts_token', t); }
function removeToken() { localStorage.removeItem('ts_token'); localStorage.removeItem('ts_user'); }
function setUser(u)    { localStorage.setItem('ts_user', JSON.stringify(u)); }
function getUser()     { try { return JSON.parse(localStorage.getItem('ts_user')); } catch { return null; } }

function decodeToken(token) {
  try {
    const payload = token.split('.')[1];
    return JSON.parse(atob(payload));
  } catch {
    return null;
  }
}

function isTokenExpired(token) {
  const decoded = decodeToken(token);
  if (!decoded || !decoded.exp) return true;
  return decoded.exp * 1000 < Date.now();
}

async function apiCall(endpoint, body = {}, method = 'POST') {
  try {
    const headers = { 'Content-Type': 'application/json' };
    const token = getToken();
    if (token) headers['Authorization'] = `Bearer ${token}`;

    const options = { method, headers };
    if (method !== 'GET') options.body = JSON.stringify(body);

    const res  = await fetch(`${API_BASE}${endpoint}`, options);
    const data = await res.json();
    return { ok: res.ok, data, status: res.status };
  } catch (err) {
    console.error('API call failed:', err);
    return { ok: false, data: { error: 'Cannot reach server. Make sure Flask is running.' } };
  }
}


async function requireAuth(redirectIfAdmin = false) {
  const token = getToken();
  if (!token || isTokenExpired(token)) {
    removeToken();
    window.location.href = 'login.html';
    return null;
  }
  const decoded = decodeToken(token);
  if (!decoded) {
    removeToken();
    window.location.href = 'login.html';
    return null;
  }
  if (redirectIfAdmin && decoded.is_admin) {
    window.location.href = 'admin.html';
    return null;
  }
  return decoded;
}

async function requireAdmin() {
  const token = getToken();
  if (!token || isTokenExpired(token)) {
    removeToken();
    window.location.href = 'login.html';
    return null;
  }
  const decoded = decodeToken(token);
  if (!decoded || !decoded.is_admin) {
    window.location.href = 'login.html';
    return null;
  }
  return decoded;
}

async function doLogout() {
  await apiCall('/api/logout', {});
  removeToken();
  window.location.href = 'login.html';
}

function initCursor() {
  const dot  = document.querySelector('.cursor-dot');
  const ring = document.querySelector('.cursor-ring');
  if (!dot || !ring) return;

  let mouseX = 0, mouseY = 0;
  let ringX  = 0, ringY  = 0;

  document.addEventListener('mousemove', e => {
    mouseX = e.clientX;
    mouseY = e.clientY;
    dot.style.left = mouseX + 'px';
    dot.style.top  = mouseY + 'px';
  });

  (function animateRing() {
    ringX += (mouseX - ringX) * 0.25;
    ringY += (mouseY - ringY) * 0.25;
    ring.style.left = ringX + 'px';
    ring.style.top  = ringY + 'px';
    requestAnimationFrame(animateRing);
  })();

  document.addEventListener('mouseleave', () => {
    dot.style.opacity = ring.style.opacity = '0';
  });
  document.addEventListener('mouseenter', () => {
    dot.style.opacity = ring.style.opacity = '1';
  });
  document.addEventListener('mousedown', () => {
    dot.style.transform = 'translate(-50%,-50%) scale(2)';
  });
  document.addEventListener('mouseup', () => {
    dot.style.transform = 'translate(-50%,-50%) scale(1)';
  });
}

function initParticles() {
  const canvas = document.getElementById('particles');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');

  const resize = () => {
    canvas.width  = window.innerWidth;
    canvas.height = window.innerHeight;
  };
  resize();
  window.addEventListener('resize', resize);

  const pts = Array.from({ length: 60 }, () => ({
    x:  Math.random() * canvas.width,
    y:  Math.random() * canvas.height,
    r:  Math.random() * 1.2 + 0.3,
    vx: (Math.random() - 0.5) * 0.25,
    vy: (Math.random() - 0.5) * 0.25,
    a:  Math.random() * 0.4 + 0.1
  }));

  (function draw() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    for (let i = 0; i < pts.length; i++) {
      for (let j = i + 1; j < pts.length; j++) {
        const dx = pts[i].x - pts[j].x, dy = pts[i].y - pts[j].y;
        const d  = Math.sqrt(dx * dx + dy * dy);
        if (d < 120) {
          ctx.strokeStyle = `rgba(200,169,126,${(1 - d / 120) * 0.07})`;
          ctx.lineWidth   = 0.5;
          ctx.beginPath();
          ctx.moveTo(pts[i].x, pts[i].y);
          ctx.lineTo(pts[j].x, pts[j].y);
          ctx.stroke();
        }
      }
    }
    pts.forEach(p => {
      p.x = (p.x + p.vx + canvas.width)  % canvas.width;
      p.y = (p.y + p.vy + canvas.height) % canvas.height;
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(200,169,126,${p.a})`;
      ctx.fill();
    });
    requestAnimationFrame(draw);
  })();
}