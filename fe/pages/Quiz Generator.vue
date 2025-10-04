<template>
  <div class="flex min-h-screen p-6 gap-6 bg-pink-50 font-sans">
    <!-- Left Column: Prompt + Preview -->
    <div class="flex-1 flex flex-col">
      <!-- Header -->
      <h2 class="text-3xl font-bold mb-4 text-pink-600 drop-shadow-sm">✨ Quiz Generator ✨</h2>

      <!-- Response / Preview -->
      <div class="flex-1 overflow-auto border-2 border-pink-200 rounded-3xl p-5 bg-pink-100 mb-4 shadow-inner">
        <h3 class="font-semibold mb-2 text-pink-700">🎉 Generated Quiz</h3>
        <div v-if="quizResponse">
          <pre class="whitespace-pre-wrap">{{ quizResponse }}</pre>
        </div>
        <p v-else class="text-pink-400 italic">Your adorable quiz will appear here...</p>
      </div>

      <!-- Prompt Input at Bottom -->
      <div class="flex gap-3">
        <textarea
          v-model="promptText"
          placeholder="Type your magical prompt here..."
          class="flex-1 border-2 border-pink-200 rounded-3xl p-4 h-28 resize-none focus:outline-none focus:ring-4 focus:ring-pink-300 bg-pink-50 placeholder-pink-300"
        ></textarea>
        <button
          @click="submitPrompt"
          class="bg-pink-500 text-white px-6 py-4 rounded-3xl font-bold hover:bg-pink-600 transition-all shadow-lg hover:scale-105"
        >
          Generate ✨
        </button>
      </div>
    </div>

    <!-- Right Column: Quiz Settings -->
    <div class="w-72 border-2 border-pink-200 rounded-3xl p-5 bg-pink-50 flex-shrink-0 shadow-md">
      <h3 class="text-xl font-semibold mb-4 text-pink-700">⚙️ Quiz Settings</h3>

      <!-- Time Limit -->
      <div class="mb-4">
        <label class="block mb-1 font-medium text-pink-600">⏰ Time Limit (minutes)</label>
        <input
          type="number"
          min="0"
          v-model.number="timeLimit"
          class="border-2 border-pink-200 rounded-full p-2 w-full focus:ring-2 focus:ring-pink-300"
        />
      </div>

      <!-- Number of Questions -->
      <div class="mb-4">
        <label class="block mb-1 font-medium text-pink-600">📝 Number of Questions</label>
        <input
          type="number"
          min="1"
          v-model.number="numQuestions"
          class="border-2 border-pink-200 rounded-full p-2 w-full focus:ring-2 focus:ring-pink-300"
        />
      </div>

      <!-- Default Question Type -->
      <div class="mb-4">
        <label class="block mb-1 font-medium text-pink-600">❓ Default Question Type</label>
        <select
          v-model="defaultQuestionType"
          class="border-2 border-pink-200 rounded-full p-2 w-full focus:ring-2 focus:ring-pink-300 bg-pink-50"
        >
          <option value="mcq">Multiple Choice</option>
          <option value="truefalse">True / False</option>
          <option value="short">Short Answer</option>
        </select>
      </div>

      <!-- Difficulty Slider -->
      <div>
        <label class="block mb-1 font-medium text-pink-600">💪 Difficulty</label>
        <input
          type="range"
          min="1"
          max="5"
          step="1"
          v-model.number="difficulty"
          class="w-full accent-pink-400"
        />
        <div class="text-sm text-pink-700 mt-1">Level: {{ difficulty }}</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from "vue";

const promptText = ref("");
const quizResponse = ref("");

// Quiz settings
const timeLimit = ref(30); // minutes
const numQuestions = ref(5);
const defaultQuestionType = ref("mcq");
const difficulty = ref(3); // 1 to 5

async function submitPrompt() {
  if (!promptText.value) return;

  // Simulate generating a quiz (replace with API call)
  quizResponse.value = "Generating quiz...\n\n";
  setTimeout(() => {
    quizResponse.value = `✨ Quiz generated from prompt: "${promptText.value}" ✨\n
⏰ Time limit: ${timeLimit.value} minutes
📝 Number of questions: ${numQuestions.value}
❓ Default type: ${defaultQuestionType.value}
💪 Difficulty: ${difficulty.value}/5

${Array.from({ length: numQuestions.value }, (_, i) => `${i + 1}. Question ${i + 1} (${defaultQuestionType.value})`).join("\n")}`;
  }, 1000);

  promptText.value = ""; // clear input after submission
}
</script>

<style>
/* Optional: cute scrollbar */
::-webkit-scrollbar {
  width: 8px;
}
::-webkit-scrollbar-track {
  background: #ffe4e6;
  border-radius: 8px;
}
::-webkit-scrollbar-thumb {
  background: #f472b6;
  border-radius: 8px;
}
</style>
