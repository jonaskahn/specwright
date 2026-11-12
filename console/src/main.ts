import { mount } from 'svelte';
import './styles/tokens.css';
import './styles/shell.css';
import './styles/components.css';
import App from './App.svelte';
import { startApp } from './lib/data/store.svelte';

startApp();
mount(App, { target: document.getElementById('app')! });
