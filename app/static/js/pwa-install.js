(() => {
  'use strict';

  // Direct native PWA installation, matching the SecureCloudStorage flow.
  // The install card is intentionally non-blocking and is shown only when the
  // browser exposes beforeinstallprompt. It is limited to once per session.
  let deferredInstallPrompt = null;
  let installCard = null;
  let installButton = null;

  const SESSION_KEY = 'mandalFinanceInstallShown_v1';

  const isStandalone = () =>
    window.matchMedia('(display-mode: standalone)').matches ||
    window.navigator.standalone === true;

  const isHomePage = () => {
    const path = window.location.pathname.replace(/\/+$/, '') || '/';
    return path === '/';
  };

  const alreadyShownThisSession = () => {
    try {
      return sessionStorage.getItem(SESSION_KEY) === 'true';
    } catch (_) {
      return false;
    }
  };

  const markShownThisSession = () => {
    try {
      sessionStorage.setItem(SESSION_KEY, 'true');
    } catch (_) {
      // Session storage may be unavailable in privacy-restricted contexts.
    }
  };

  const removeCard = () => {
    if (installCard) {
      installCard.remove();
      installCard = null;
      installButton = null;
    }
  };

  const createCard = () => {
    if (installCard || isStandalone() || !isHomePage() || alreadyShownThisSession() || !deferredInstallPrompt) return;

    const style = document.createElement('style');
    style.id = 'mandal-pwa-install-style';
    style.textContent = `
      #mandalPwaInstallCard {
        position: fixed;
        right: 20px;
        bottom: 20px;
        z-index: 1080;
        width: min(360px, calc(100vw - 32px));
        padding: 18px;
        border: 1px solid rgba(255,255,255,.18);
        border-radius: 18px;
        background: rgba(15,23,42,.96);
        color: #fff;
        box-shadow: 0 18px 50px rgba(0,0,0,.28);
        backdrop-filter: blur(14px);
        -webkit-backdrop-filter: blur(14px);
        animation: mandalPwaInstallIn .28s ease-out;
      }
      #mandalPwaInstallCard .mandal-pwa-close {
        position: absolute;
        top: 9px;
        right: 11px;
        width: 28px;
        height: 28px;
        border: 0;
        border-radius: 50%;
        background: transparent;
        color: rgba(255,255,255,.7);
        font-size: 21px;
        line-height: 1;
        cursor: pointer;
      }
      #mandalPwaInstallCard .mandal-pwa-close:hover { background: rgba(255,255,255,.1); color: #fff; }
      #mandalPwaInstallCard .mandal-pwa-icon {
        width: 46px;
        height: 46px;
        border-radius: 13px;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        background: rgba(245,158,11,.16);
        font-size: 23px;
        margin-bottom: 11px;
      }
      #mandalPwaInstallCard h3 { margin: 0 30px 6px 0; font: 700 1.05rem/1.25 Outfit, sans-serif; }
      #mandalPwaInstallCard p { margin: 0 0 14px; color: rgba(255,255,255,.72); font: 400 .9rem/1.45 'Plus Jakarta Sans', sans-serif; }
      #mandalPwaInstallCard .mandal-pwa-install {
        width: 100%;
        border: 0;
        border-radius: 11px;
        padding: 10px 14px;
        background: #f59e0b;
        color: #111827;
        font: 700 .92rem/1.2 Outfit, sans-serif;
        cursor: pointer;
      }
      #mandalPwaInstallCard .mandal-pwa-install:hover { filter: brightness(1.06); }
      @keyframes mandalPwaInstallIn { from { opacity: 0; transform: translateY(14px); } to { opacity: 1; transform: translateY(0); } }
      @media (max-width: 576px) {
        #mandalPwaInstallCard { right: 12px; bottom: 12px; width: calc(100vw - 24px); padding: 16px; }
      }
    `;
    document.head.appendChild(style);

    const card = document.createElement('aside');
    card.id = 'mandalPwaInstallCard';
    card.setAttribute('role', 'dialog');
    card.setAttribute('aria-label', 'Install Mandal Finance app');
    card.innerHTML = `
      <button type="button" class="mandal-pwa-close" aria-label="Not now">&times;</button>
      <div class="mandal-pwa-icon" aria-hidden="true">📱</div>
      <h3>Install Mandal Finance</h3>
      <p>Install the Mandal Finance app for faster access and an app-like experience.</p>
      <button type="button" class="mandal-pwa-install">Install app</button>
    `;

    document.body.appendChild(card);
    installCard = card;
    installButton = card.querySelector('.mandal-pwa-install');

    card.querySelector('.mandal-pwa-close')?.addEventListener('click', removeCard);
    installButton?.addEventListener('click', async () => {
      if (!deferredInstallPrompt) {
        removeCard();
        return;
      }

      deferredInstallPrompt.prompt();
      const result = await deferredInstallPrompt.userChoice;
      deferredInstallPrompt = null;

      if (result?.outcome === 'accepted') {
        removeCard();
      } else if (installButton) {
        installButton.disabled = true;
        installButton.textContent = 'Install dismissed';
      }
    });

    markShownThisSession();
  };

  window.addEventListener('beforeinstallprompt', (event) => {
    event.preventDefault();
    deferredInstallPrompt = event;
    createCard();
  });

  window.addEventListener('appinstalled', () => {
    deferredInstallPrompt = null;
    removeCard();
  });
})();
