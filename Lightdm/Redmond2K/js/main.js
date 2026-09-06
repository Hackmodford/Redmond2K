container_interval_id = 0;
password_interval_id = 0;
distro_image = 'ubuntu.svg';
selected_session = null;

// The real, unmasked value of #password. The field itself only ever shows
// asterisks (or, for a visible prompt, the literal text) - see maskSecretInput.
real_secret = '';
// Whether #password should render as asterisks. True by default since it
// starts life as the password field; show_prompt flips it per PAM prompt type.
mask_secret = true;

// Keeps #password showing '*' per real character (Win2k used asterisks, not
// the bullet dots a native type="password" field would render) while tracking
// the actual typed value in real_secret. Runs on every keystroke/paste/cut.
function maskSecretInput(e) {
    var el = document.getElementById('password');
    if (!mask_secret) {
        real_secret = el.value;
        return;
    }
    var displayed = el.value;
    var caret = el.selectionStart;
    if (displayed.length > real_secret.length) {
        // Characters were inserted (typed or pasted) ending at the caret
        var insertedCount = displayed.length - real_secret.length;
        var insertPos = caret - insertedCount;
        var inserted = displayed.substring(insertPos, caret);
        real_secret = real_secret.slice(0, insertPos) + inserted + real_secret.slice(insertPos);
    } else if (displayed.length < real_secret.length) {
        // Characters were removed (backspace/delete/cut) ending at the caret
        var deletedCount = real_secret.length - displayed.length;
        real_secret = real_secret.slice(0, caret) + real_secret.slice(caret + deletedCount);
    }
    el.value = new Array(real_secret.length + 1).join('*');
    el.setSelectionRange(caret, caret);
}

// Shows an error
function show_error(text) {
	setFormBusy(false);
	show_message(text, "error");
	// Stop the script on error
	throw new Error();
}

// Shows the Win2k-style "Logon Message" modal (used for both info and error text)
function showMessageDialog(text, type) {
    var icon = document.getElementById('message-dialog-icon');
    document.getElementById('message-dialog-text').textContent = text;
    icon.src = type === 'error' ? 'img/dialog-error.png' : 'img/dialog-info.png';
    icon.alt = type === 'error' ? 'Error' : 'Information';
    document.getElementById('message-dialog').classList.add('open');
    document.getElementById('message-dialog-ok').focus();
}

function hideMessageDialog() {
    document.getElementById('message-dialog').classList.remove('open');
    // Safety net: guarantees the form is never left stuck disabled behind a
    // dialog, regardless of what greyed it out (a real auth attempt already
    // re-enables it itself; this covers every other/future caller too)
    setFormBusy(false);
}

// Called by lightdm when it needs to display an info or error message outside
// of the normal prompt/auth flow (e.g. a PAM password-expiry or lockout notice)
function show_message(text, type) {
    showMessageDialog(text, type);
}

// Pins beveled controls to whole pixels so their 1px edges map to whole
// device pixels (authored px * TARGET_SCALE) and stay crisp after scaling
function snapControls() {
    var els = document.querySelectorAll('button, #form form input, #session-combo');
    for (var i = 0; i < els.length; i++) {
        els[i].style.width = '';
        els[i].style.height = '';
    }
    for (var j = 0; j < els.length; j++) {
        els[j].style.width = els[j].offsetWidth + 'px';
        els[j].style.height = els[j].offsetHeight + 'px';
    }
}

// Center the main login container
function centerContainer() {
    var container = document.getElementById("box");
    // Whole-pixel control sizes keep each edge on the device grid once scaled
    snapControls();
    // offsetWidth/Height are pre-transform, matching the coordinate space of top/left
    // Round so the container origin lands on whole authored pixels (crisp bevels)
    // Biased above true vertical center (40% of the leftover space above vs. 50%) - looks better than dead center
    container.style.top = Math.round((document.body.clientHeight - container.offsetHeight) * 0.3) + 'px';
    container.style.left = Math.round((document.body.clientWidth - container.offsetWidth) / 2) + 'px';
}

// Centers the main container on container resize
// Time to build a custom resize event emulator thingy!
function centerContainerOnResize() {
    onResize(document.getElementById('box'), centerContainer);
}

// Executes a callback when an element is resized
function onResize(el, callback) {
    var width = el.offsetWidth;
    var height = el.offsetHeight;

    container_interval_id = setInterval(function() {
        // If the width or height don't match up
        if( el.offsetWidth != width || el.offsetHeight != height ) {
            // Remove the old task (with the old width/height)
            clearInterval(container_interval_id);
            // Execute the callback
            if(callback) callback();
            // And bind a new resize event (this makes sure we're always checking against the new width/height)
            onResize(el, callback);
        }
    },250);
}

// Greys out (and disables) the login form while an authentication attempt is in flight
function setFormBusy(busy) {
    document.getElementById('user').disabled = busy;
    document.getElementById('password').disabled = busy;
    document.getElementById('session-combo').classList.toggle('disabled', busy);
    document.getElementById('login-submit').disabled = busy;
}

// This is called by lightdm when the auth request is completed
function authentication_complete() {
    if (lightdm.is_authenticated) {
	lightdm.start_session_sync(selected_session);
    } else {
        setFormBusy(false);
        show_message("Authentication failed", "error");
        // Guarded: throws if the backend already tore down the auth session
        // by the time this fires, since there's then nothing left to cancel
        try { lightdm.cancel_authentication(); } catch (e) {}
    }
}

// Called by lightdm when an autologin user's timer expires; reset the auth flow
function autologin_timer_expired() {
    lightdm.cancel_authentication();
}

// Ignore requests for timed logins
function timed_login(user) {}

// Attempts to log in with lightdm
// Executes on form submit
function attemptLogin() {
    setFormBusy(true);
    // Cancel weird timed logins
    lightdm.cancel_autologin();
    // Pass on user to lightdm
    var user = document.getElementById('user').value;
    lightdm.authenticate(user);
}

// Called by lightdm when it wants us to show a prompt. "type" is "password"
// for a prompt whose input should be hidden, or "text" for a visible one
// (e.g. a one-time code) - only mask the field with asterisks in that case.
function show_prompt(text, type) {
    mask_secret = (type !== 'text');
    // Pass on the response to lightdm once we have actually started authenticating
	if(password_interval_id > 0) clearInterval(password_interval_id);
	password_interval_id = setInterval(function() {
        lightdm.respond(real_secret);
	}, 250);
}

// Updates elements with content like time, etc.
function initializeWidgets() {
    // Start up the clock
   // initializeClockWidget();
    // Start up the hostname widget
    //initializeHostnameWidget();
    // Start up the distro widget
    //initializeDistroWidget();
}

function initializeDistroWidget() {	
	// If we have a distro image
	if(distro_image) {
		// Add in the distro logo
		var el = document.getElementById('distro-widget');
		var img = document.createElement('img');
		
		el.appendChild(img);
		
		img.src = 'img/distro/'+distro_image;
		
		// Center the form elements in #form after the image has loaded
		img.onload = function() {
			var form = document.getElementById('form');
			var content = document.getElementById('content');
			// Set #form top margin to half of #content height minus half of #form height
			form.style.marginTop = ((content.offsetHeight / 2) - (form.offsetHeight / 2)) + 'px';
		}
	}
}

function initializeClockWidget() {
    updateClockWidget();
    setInterval(updateClockWidget, 1000);
}

function initializeHostnameWidget() {
    var el = document.getElementById("hostname-widget");
    el.innerHTML = lightdm.hostname;
}

function updateClockWidget() {
    var el = document.getElementById("clock-widget");
    var date = new Date();

    var days = ['Sunday','Monday','Tuesday','Wednesday','Thursday','Friday','Saturday'];
    var months = ['January','February','March','April','May','June','July','August','September','October','November','December'];

    var dateString = '<span>' + (date.getHours()<10?'0':'') + date.getHours() + ':' + (date.getMinutes()<10?'0':'') + date.getMinutes() + '</span>'; 
    el.innerHTML = dateString;
}

//If we have a logged in user, add his username to the user field
function initializeUsers() {
    var el = document.getElementById('user');

    // Loop through users
    for (var i = 0; i < lightdm.users.length; i++) {
        var user = lightdm.users[i];
        if(user.logged_in) {
            el.value = user.name;
        }
    }
}

// Loads actions like suspend, reboot, etc.
function initializeActions() {
    bindAction('action-shutdown', lightdm.can_shutdown, lightdm.shutdown);
    bindAction('action-restart', lightdm.can_restart, lightdm.restart);
    bindAction('action-suspend', lightdm.can_suspend, lightdm.suspend);
}

// Wires up a power action button, hiding it when unsupported
function bindAction(id, enabled, action) {
    var el = document.getElementById(id);
    if (!enabled) {
        el.style.display = 'none';
        return;
    }
    el.onclick = function(e) {
        action();
        e.stopPropagation();
        e.preventDefault(true);
        return false;
    };
}

// Dev-only preview controls for the Logon Message dialog; only created when
// running against js/mock.js, never present against the real lightdm bridge
function initializeDebugPanel() {
    if (!lightdm._is_mock) return;

    var panel = document.createElement('div');
    panel.id = 'debug-panel';

    var infoBtn = document.createElement('button');
    infoBtn.type = 'button';
    infoBtn.textContent = 'Debug: info message';
    infoBtn.onclick = function() { show_message('Your password will expire in 3 days.', 'info'); };

    var errorBtn = document.createElement('button');
    errorBtn.type = 'button';
    errorBtn.textContent = 'Debug: error message';
    errorBtn.onclick = function() { show_message('The system could not log you on.', 'error'); };

    var disabledBtn = document.createElement('button');
    disabledBtn.type = 'button';
    disabledBtn.textContent = 'Debug: toggle disabled';
    disabledBtn.onclick = function() { setFormBusy(!document.getElementById('user').disabled); };

    panel.appendChild(infoBtn);
    panel.appendChild(errorBtn);
    panel.appendChild(disabledBtn);
    document.body.appendChild(panel);
}

// Returns the lightdm user record for a username, or null
function findUser(name) {
    for (var i = 0; i < lightdm.users.length; i++) {
        if (lightdm.users[i].name == name) return lightdm.users[i];
    }
    return null;
}

// Selects the session lightdm remembers for the user in the username field,
// falling back to the system default
function applyPreferredSession() {
    var user = findUser(document.getElementById('user').value);
    var key = (user && user.session) || (lightdm.default_session && lightdm.default_session.key);

    for (var i = 0; i < lightdm.sessions.length; i++) {
        if (lightdm.sessions[i].key == key) {
            selectSession(lightdm.sessions[i].key, lightdm.sessions[i].name);
            return;
        }
    }
}

// Populates the session dropdown with the available sessions
function initializeSessions() {
    var combo = document.getElementById('session-combo');
    var list = document.getElementById('session-list');
    list.innerHTML = '';

    for (var i = 0; i < lightdm.sessions.length; i++) {
        var session = lightdm.sessions[i];
        var item = document.createElement('li');
        item.textContent = session.name;
        item.setAttribute('data-key', session.key);
        // Hovering the mouse re-selects live, same as arrow keys, so there is
        // only ever one highlighted row - matches real Win32 hot-tracking
        item.onmouseenter = function() {
            selectSession(this.getAttribute('data-key'), this.textContent);
        };
        item.onclick = function(e) {
            selectSession(this.getAttribute('data-key'), this.textContent);
            combo.classList.remove('open');
            e.stopPropagation();
        };
        list.appendChild(item);

        if (!selected_session) {
            selectSession(session.key, session.name);
        }
    }

    applyPreferredSession();

    // Follow the user's remembered session as the username is edited
    document.getElementById('user').addEventListener('change', applyPreferredSession);

    combo.onclick = function() {
        combo.classList.toggle('open');
    };

    // Close the list when clicking anywhere else
    document.addEventListener('click', function(e) {
        if (!combo.contains(e.target)) combo.classList.remove('open');
    });

    // Keyboard support, matching a real Win32 dropdown-list combo box:
    // arrow keys change the selection directly and live (whether or not the
    // list is dropped down), F4/Alt+Up/Alt+Down open or close the list,
    // Escape closes it, and typing a letter jumps to the next matching
    // session. Enter closes the list when it's open (confirming the live
    // selection, same as the list itself capturing Enter in real Windows),
    // but is otherwise left alone so it falls through to submitting the
    // login form, rather than always being swallowed by the combo.
    combo.addEventListener('keydown', function(e) {
        var idx = -1;
        for (var i = 0; i < lightdm.sessions.length; i++) {
            if (lightdm.sessions[i].key == selected_session) {
                idx = i;
                break;
            }
        }

        if (e.key === 'F4' || ((e.key === 'ArrowDown' || e.key === 'ArrowUp') && e.altKey)) {
            combo.classList.toggle('open');
            e.preventDefault();
        } else if (e.key === 'ArrowDown' && idx < lightdm.sessions.length - 1) {
            selectSession(lightdm.sessions[idx + 1].key, lightdm.sessions[idx + 1].name);
            e.preventDefault();
        } else if (e.key === 'ArrowUp' && idx > 0) {
            selectSession(lightdm.sessions[idx - 1].key, lightdm.sessions[idx - 1].name);
            e.preventDefault();
        } else if (e.key === 'Escape' || (e.key === 'Enter' && combo.classList.contains('open'))) {
            combo.classList.remove('open');
            e.preventDefault();
        } else if (e.key.length === 1 && !e.ctrlKey && !e.altKey && !e.metaKey) {
            var letter = e.key.toLowerCase();
            var n = lightdm.sessions.length;
            for (var j = 1; j <= n; j++) {
                var candidate = lightdm.sessions[(idx + j) % n];
                if (candidate.name.charAt(0).toLowerCase() === letter) {
                    selectSession(candidate.key, candidate.name);
                    break;
                }
            }
            e.preventDefault();
        }
    });
}

// Records the chosen session and updates the combo box display
function selectSession(key, name) {
    selected_session = key;
    document.getElementById('session-value').textContent = name;

    var items = document.getElementById('session-list').children;
    for (var i = 0; i < items.length; i++) {
        items[i].className = items[i].getAttribute('data-key') == key ? 'selected' : '';
    }
}

// Focuses the user field (if empty), else focuses the password field
function handleFocus() {
	var user = document.getElementById('user');
	if(user.value == 'undefined' || user.value == '') {
		user.focus();
	}else{
		document.getElementById('password').focus();
	}
}

// Desired total UI scale factor (2 = HiDPI/4K)
var TARGET_SCALE = 2;

// Scales the whole UI. Uses transform rather than zoom because WebKit does not
// scale mouse hit-testing with zoom, which offsets hover/click targets.
// scale * devicePixelRatio stays === TARGET_SCALE so one authored pixel always
// maps to a whole number of device pixels, keeping the 1px bevels crisp.
function applyScale() {
    var scale = TARGET_SCALE / (window.devicePixelRatio || 1);
    var body = document.body;
    body.style.transformOrigin = '0 0';
    body.style.transform = 'scale(' + scale + ')';
    body.style.width = (100 / scale) + 'vw';
    body.style.height = (100 / scale) + 'vh';
}

// Re-applies scaling, snapping and centering. Must run whenever the viewport or
// devicePixelRatio changes, otherwise a stale scale breaks the whole-pixel mapping.
function relayout() {
    applyScale();
    centerContainer();
}

// Initializes the script
(function initialize() {
    relayout();
    // Re-run on viewport or devicePixelRatio changes so scaling stays whole-pixel
    window.addEventListener('resize', relayout);
    // Center container again on container resize
    centerContainerOnResize();
    // Update elements that contain informations like time, date, hostname, etc.
    // initializeWidgets();
    // Load the list of users
    initializeUsers();
    // Load the list of sessions
    initializeSessions();
    // Mask #password with asterisks as it's typed
    document.getElementById('password').addEventListener('input', maskSecretInput);
    // Load actions (suspend, reboot, shutdown, etc.)
    initializeActions();
    // Handle focusing
    handleFocus();
    // Wire up the Logon Message dialog's OK button
    document.getElementById('message-dialog-ok').onclick = hideMessageDialog;
    // Dev-only: show preview buttons for the Logon Message dialog when mocked
    initializeDebugPanel();
})();
