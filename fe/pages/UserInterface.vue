<!-- UserInterface.yue -->
<template>
  <div class="user-interface">
    <header class="ui-header">
      <h1>Welcome to Your App</h1>
    </header>

    <main class="ui-main">
      <section class="ui-section">
        <h2>Sample Controls</h2>
        <input 
          v-model="userInput" 
          type="text" 
          placeholder="Type something..."
        />
        <button @click="handleClick">Submit</button>
        <p v-if="submittedText">You submitted: {{ submittedText }}</p>
      </section>

      <section class="ui-section">
        <h2>Example List</h2>
        <ul>
          <li v-for="(item, index) in items" :key="index">{{ item }}</li>
        </ul>
      </section>
    </main>

    <footer class="ui-footer">
      <p>&copy; 2025 Your App</p>
    </footer>
  </div>
</template>

<script setup>
import { ref } from 'vue'

// reactive state variables
const userInput = ref('')
const submittedText = ref('')
const items = ref(['Item 1', 'Item 2', 'Item 3'])

// handle button click
function handleClick() {
  submittedText.value = userInput.value
  userInput.value = ''
}
</script>

<style scoped>
.user-interface {
  font-family: Arial, sans-serif;
  margin: 2rem;
}

.ui-header, .ui-footer {
  text-align: center;
  margin-bottom: 1.5rem;
}

.ui-main {
  display: flex;
  gap: 2rem;
  justify-content: center;
}

.ui-section {
  border: 1px solid #ccc;
  padding: 1rem;
  border-radius: 8px;
  width: 300px;
}

button {
  margin-top: 0.5rem;
  padding: 0.5rem 1rem;
  cursor: pointer;
}
</style>
