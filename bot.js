require('dotenv').config();
const TelegramBot = require('node-telegram-bot-api');
const { GoogleGenerativeAI } = require('@google/generative-ai');
const { chromium } = require('playwright');
const { execSync } = require('child_process');
const fs = require('fs');
const https = require('https');

const bot = new TelegramBot(process.env.TELEGRAM_BOT_TOKEN, { polling: true });
const genai = new GoogleGenerativeAI(process.env.GEMINI_API_KEY);
const ALLOWED_CHAT_ID = parseInt(process.env.TELEGRAM_CHAT_ID);

const HISTORY_FILE = '/Users/salim/claude/conversation_history.json';

function loadHistory() {
  try {
    if (fs.existsSync(HISTORY_FILE)) {
      const data = JSON.parse(fs.readFileSync(HISTORY_FILE, 'utf8'));
      // Validate Gemini format — entries must have 'parts', not 'content'
      if (data.length === 0 || data[0].parts) return data;
      console.log('Old history format detected, starting fresh.');
    }
  } catch (e) {
    console.error('Failed to load history:', e.message);
  }
  return [];
}

function saveHistory() {
  try {
    fs.writeFileSync(HISTORY_FILE, JSON.stringify(conversationHistory, null, 2));
  } catch (e) {
    console.error('Failed to save history:', e.message);
  }
}

const conversationHistory = loadHistory();
let browser = null;
let page = null;

console.log('Bot is running...');

// ─── Browser ────────────────────────────────────────────────────────────────

async function getPage() {
  if (!browser) {
    browser = await chromium.launch({ headless: false });
  }
  if (!page || page.isClosed()) {
    page = await browser.newPage();
  }
  return page;
}

// ─── Utilities ───────────────────────────────────────────────────────────────

function downloadFile(fileUrl, destPath) {
  return new Promise((resolve, reject) => {
    const file = fs.createWriteStream(destPath);
    https.get(fileUrl, (response) => {
      response.pipe(file);
      file.on('finish', () => { file.close(); resolve(); });
    }).on('error', reject);
  });
}

function takeScreenshot() {
  const filePath = `/tmp/screenshot_${Date.now()}.png`;
  execSync(`screencapture -x ${filePath}`);
  return filePath;
}

async function textToVoice(text, chatId) {
  const aiffPath = `/tmp/voice_${Date.now()}.aiff`;
  const mp3Path = aiffPath.replace('.aiff', '.mp3');
  try {
    execSync(`say -o ${aiffPath} "${text.replace(/"/g, "'")}"`);
    execSync(`ffmpeg -y -i ${aiffPath} ${mp3Path} 2>/dev/null`);
    await bot.sendVoice(chatId, mp3Path);
    fs.unlinkSync(aiffPath);
    fs.unlinkSync(mp3Path);
    return true;
  } catch (e) {
    console.error('TTS error:', e.message);
    return false;
  }
}

async function transcribeAudio(audioPath) {
  const audioData = fs.readFileSync(audioPath).toString('base64');
  const model = genai.getGenerativeModel({ model: 'gemini-3.0-flash' });
  const result = await model.generateContent([
    { inlineData: { data: audioData, mimeType: 'audio/ogg' } },
    'Transcribe this audio message accurately. Output only the transcription, nothing else.',
  ]);
  return result.response.text().trim();
}

// ─── Tool execution (unchanged) ──────────────────────────────────────────────

async function executeTool(name, input) {
  console.log(`Tool: ${name}`, input);
  try {
    if (name === 'open_app') {
      execSync(`open -a "${input.app_name}"`);
      return `Opened ${input.app_name}`;
    }
    if (name === 'run_command') {
      const output = execSync(input.command, { encoding: 'utf8', timeout: 15000 });
      return output || '(no output)';
    }
    if (name === 'run_applescript') {
      const output = execSync(`osascript -e '${input.script.replace(/'/g, '"')}'`, { encoding: 'utf8', timeout: 15000 });
      return output || '(done)';
    }
    if (name === 'browser_navigate') {
      const p = await getPage();
      await p.goto(input.url, { waitUntil: 'domcontentloaded', timeout: 15000 });
      return `Navigated to ${input.url}`;
    }
    if (name === 'browser_click') {
      const p = await getPage();
      await p.click(input.selector, { timeout: 10000 });
      return `Clicked ${input.selector}`;
    }
    if (name === 'browser_type') {
      const p = await getPage();
      await p.fill(input.selector, input.text);
      return `Typed into ${input.selector}`;
    }
    if (name === 'browser_screenshot') {
      const p = await getPage();
      const imgPath = `/tmp/browser_${Date.now()}.png`;
      await p.screenshot({ path: imgPath });
      return { type: 'screenshot', path: imgPath };
    }
    if (name === 'browser_get_content') {
      const p = await getPage();
      const text = await p.innerText('body');
      return text.slice(0, 3000);
    }
    if (name === 'read_file') {
      const content = fs.readFileSync(input.path, 'utf8');
      return content.slice(0, 8000);
    }
    if (name === 'save_file') {
      const dir = require('path').dirname(input.destination);
      if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
      fs.copyFileSync(input.source, input.destination);
      if (input.delete_source) fs.unlinkSync(input.source);
      return `Saved to ${input.destination}`;
    }
    return `Unknown tool: ${name}`;
  } catch (e) {
    return `Error: ${e.message}`;
  }
}

// ─── Tool definitions (Gemini functionDeclarations format) ───────────────────

const FUNCTION_DECLARATIONS = [
  {
    name: 'open_app',
    description: 'Open a Mac application by name',
    parameters: {
      type: 'object',
      properties: {
        app_name: { type: 'string', description: 'Application name, e.g. "Safari", "Spotify", "Notes"' }
      },
      required: ['app_name']
    }
  },
  {
    name: 'run_command',
    description: 'Run a shell command on the Mac and return the output',
    parameters: {
      type: 'object',
      properties: {
        command: { type: 'string', description: 'Shell command to execute' }
      },
      required: ['command']
    }
  },
  {
    name: 'run_applescript',
    description: 'Run an AppleScript to control Mac apps (e.g. click buttons, set volume, interact with UI)',
    parameters: {
      type: 'object',
      properties: {
        script: { type: 'string', description: 'AppleScript code to execute' }
      },
      required: ['script']
    }
  },
  {
    name: 'browser_navigate',
    description: 'Open a URL in the browser',
    parameters: {
      type: 'object',
      properties: {
        url: { type: 'string', description: 'Full URL to navigate to' }
      },
      required: ['url']
    }
  },
  {
    name: 'browser_click',
    description: 'Click an element in the browser using a CSS selector',
    parameters: {
      type: 'object',
      properties: {
        selector: { type: 'string', description: 'CSS selector of the element to click' }
      },
      required: ['selector']
    }
  },
  {
    name: 'browser_type',
    description: 'Type text into an input field in the browser',
    parameters: {
      type: 'object',
      properties: {
        selector: { type: 'string', description: 'CSS selector of the input field' },
        text: { type: 'string', description: 'Text to type' }
      },
      required: ['selector', 'text']
    }
  },
  {
    name: 'browser_screenshot',
    description: 'Take a screenshot of the current browser state and send it',
    parameters: { type: 'object', properties: {} }
  },
  {
    name: 'browser_get_content',
    description: 'Get the visible text content of the current browser page',
    parameters: { type: 'object', properties: {} }
  },
  {
    name: 'read_file',
    description: 'Read the contents of a file on the Mac',
    parameters: {
      type: 'object',
      properties: {
        path: { type: 'string', description: 'Absolute path to the file' }
      },
      required: ['path']
    }
  },
  {
    name: 'save_file',
    description: 'Save/move a file to a specific location on the Mac',
    parameters: {
      type: 'object',
      properties: {
        source: { type: 'string', description: 'Current absolute path of the file' },
        destination: { type: 'string', description: 'Destination absolute path including filename' },
        delete_source: { type: 'boolean', description: 'If true, remove the source after copying (move).' }
      },
      required: ['source', 'destination']
    }
  }
];

const model = genai.getGenerativeModel({
  model: 'gemini-3.0-flash',
  tools: [{ functionDeclarations: FUNCTION_DECLARATIONS }],
  systemInstruction: `You are a personal AI assistant called Thiago, running on the user's Mac.
You can automate tasks, answer questions, browse the web, open apps, and control the computer.
You can receive and understand voice messages — they are transcribed automatically before reaching you.
Use your tools proactively to complete tasks. For multi-step tasks, chain tools together.

Special response commands (use in your final text reply):
- To take a Mac screenshot: [SCREENSHOT]
- To send a file: [FILE:/full/path/to/file]
- To reply as a voice note: [VOICE:your message here]

Be concise and direct. Current date: ${new Date().toLocaleDateString()}.`
});

// ─── Main AI function ────────────────────────────────────────────────────────

async function askGemini(userParts, chatId = null) {
  conversationHistory.push({ role: 'user', parts: userParts });

  while (true) {
    const result = await model.generateContent({ contents: conversationHistory });
    const responseParts = result.response.candidates[0].content.parts;

    conversationHistory.push({ role: 'model', parts: responseParts });

    // Trim history — only cut at clean user turns (no functionResponse parts)
    if (conversationHistory.length > 40) {
      for (let i = 2; i < conversationHistory.length - 10; i += 2) {
        const msg = conversationHistory[i];
        const isClean = msg.role === 'user' && msg.parts.every(p => !p.functionResponse);
        if (isClean) {
          conversationHistory.splice(0, i);
          break;
        }
      }
    }

    const functionCalls = responseParts.filter(p => p.functionCall);

    if (functionCalls.length === 0) {
      saveHistory();
      const textPart = responseParts.find(p => p.text);
      return textPart ? textPart.text : '';
    }

    // Execute all function calls and collect responses
    const functionResponses = [];
    for (const part of functionCalls) {
      const { name, args } = part.functionCall;
      const toolResult = await executeTool(name, args);

      if (toolResult && toolResult.type === 'screenshot' && chatId) {
        await bot.sendPhoto(chatId, toolResult.path);
        fs.unlinkSync(toolResult.path);
        functionResponses.push({ functionResponse: { name, response: { result: 'Screenshot sent to user.' } } });
      } else {
        functionResponses.push({ functionResponse: { name, response: { result: String(toolResult) } } });
      }
    }

    conversationHistory.push({ role: 'user', parts: functionResponses });
  }
}

// ─── Message handler ─────────────────────────────────────────────────────────

bot.on('message', async (msg) => {
  const chatId = msg.chat.id;

  if (chatId !== ALLOWED_CHAT_ID) {
    bot.sendMessage(chatId, 'Unauthorized.');
    return;
  }

  bot.sendChatAction(chatId, 'typing');

  try {
    // Voice messages
    if (msg.voice) {
      const fileInfo = await bot.getFile(msg.voice.file_id);
      const fileUrl = `https://api.telegram.org/file/bot${process.env.TELEGRAM_BOT_TOKEN}/${fileInfo.file_path}`;
      const audioPath = `/tmp/voice_in_${Date.now()}.ogg`;
      await downloadFile(fileUrl, audioPath);
      const transcription = await transcribeAudio(audioPath);
      fs.unlinkSync(audioPath);
      console.log(`Voice transcription: ${transcription}`);
      const reply = await askGemini([{ text: transcription }], chatId);
      await bot.sendMessage(chatId, reply);
      return;
    }

    // Photos
    if (msg.photo) {
      const photo = msg.photo[msg.photo.length - 1];
      const fileInfo = await bot.getFile(photo.file_id);
      const fileUrl = `https://api.telegram.org/file/bot${process.env.TELEGRAM_BOT_TOKEN}/${fileInfo.file_path}`;
      const imgPath = `/tmp/photo_in_${Date.now()}.jpg`;
      await downloadFile(fileUrl, imgPath);
      const imageData = fs.readFileSync(imgPath).toString('base64');
      fs.unlinkSync(imgPath);
      const caption = msg.caption || 'What do you see in this image?';
      const reply = await askGemini([
        { inlineData: { data: imageData, mimeType: 'image/jpeg' } },
        { text: caption }
      ], chatId);
      await bot.sendMessage(chatId, reply);
      return;
    }

    // Documents/files
    if (msg.document) {
      const doc = msg.document;
      const fileInfo = await bot.getFile(doc.file_id);
      const fileUrl = `https://api.telegram.org/file/bot${process.env.TELEGRAM_BOT_TOKEN}/${fileInfo.file_path}`;
      const tmpPath = `/tmp/${doc.file_name || `file_${Date.now()}`}`;
      await downloadFile(fileUrl, tmpPath);

      const textExtensions = ['.txt', '.md', '.json', '.js', '.ts', '.py', '.sh', '.csv', '.html', '.css', '.xml', '.yaml', '.yml', '.env', '.log'];
      const ext = require('path').extname(doc.file_name || '').toLowerCase();
      const isText = textExtensions.includes(ext);

      let prompt = `The user sent a file: "${doc.file_name}" (${doc.mime_type}, ${doc.file_size} bytes). It's saved at: ${tmpPath}.`;
      if (isText) {
        const content = fs.readFileSync(tmpPath, 'utf8');
        prompt += `\n\nFile contents:\n\`\`\`\n${content.slice(0, 6000)}\n\`\`\``;
      }
      if (msg.caption) prompt += `\n\nUser's note: ${msg.caption}`;
      prompt += `\n\nDecide where to save this file on the Mac (e.g. ~/Downloads or a relevant folder), save it using the save_file tool, then confirm with the user.`;

      const reply = await askGemini([{ text: prompt }], chatId);
      await bot.sendMessage(chatId, reply);
      return;
    }

    // Text messages
    const userMessage = msg.text;
    if (!userMessage) return;

    console.log(`You: ${userMessage}`);
    const reply = await askGemini([{ text: userMessage }], chatId);
    console.log(`Thiago: ${reply}`);

    if (!reply) return;

    if (reply.includes('[SCREENSHOT]')) {
      await bot.sendMessage(chatId, 'Taking screenshot...');
      const screenshotPath = takeScreenshot();
      await bot.sendPhoto(chatId, screenshotPath);
      fs.unlinkSync(screenshotPath);
      return;
    }

    const fileMatch = reply.match(/\[FILE:(.+?)\]/);
    if (fileMatch) {
      const filePath = fileMatch[1].trim();
      if (fs.existsSync(filePath)) {
        await bot.sendDocument(chatId, filePath);
      } else {
        await bot.sendMessage(chatId, `File not found: ${filePath}`);
      }
      return;
    }

    const voiceMatch = reply.match(/\[VOICE:([\s\S]+?)\]/);
    if (voiceMatch) {
      const sent = await textToVoice(voiceMatch[1], chatId);
      if (!sent) await bot.sendMessage(chatId, voiceMatch[1]);
      return;
    }

    await bot.sendMessage(chatId, reply);

  } catch (error) {
    console.error('Error:', error.message);
    bot.sendMessage(chatId, `Error: ${error.message}`);
  }
});

bot.on('polling_error', (error) => {
  console.error('Polling error:', error.message);
});
