<template>
  <div class="login-wrap">
    <Card class="login-card" dis-hover>
      <template #title>
        <span>HyperAgents Login</span>
      </template>

      <Tabs v-model="mode" type="card">
        <TabPane label="Sign In" name="login">
          <Form :model="loginForm" :label-width="70" @submit.prevent>
            <FormItem label="Account">
              <Input v-model="loginForm.account" placeholder="username or email" />
            </FormItem>
            <FormItem label="Password">
              <Input v-model="loginForm.password" type="password" password placeholder="password" />
            </FormItem>
            <FormItem>
              <Button type="primary" long :loading="loading" @click="submitLogin">Login</Button>
            </FormItem>
          </Form>
        </TabPane>

        <TabPane label="Sign Up" name="register">
          <Form :model="registerForm" :label-width="90" @submit.prevent>
            <FormItem label="Username">
              <Input v-model="registerForm.username" placeholder="at least 3 chars" />
            </FormItem>
            <FormItem label="Display Name">
              <Input v-model="registerForm.display_name" placeholder="optional" />
            </FormItem>
            <FormItem label="Email">
              <Input v-model="registerForm.email" placeholder="optional" />
            </FormItem>
            <FormItem label="Password">
              <Input v-model="registerForm.password" type="password" password placeholder="at least 6 chars" />
            </FormItem>
            <FormItem>
              <Button type="success" long :loading="loading" @click="submitRegister">Create Account</Button>
            </FormItem>
          </Form>
        </TabPane>
      </Tabs>
    </Card>
  </div>
</template>

<script setup>
import { reactive, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { Message } from "view-ui-plus";
import { api } from "../services/api";
import { saveAuth } from "../stores/auth";

const route = useRoute();
const router = useRouter();

const loading = ref(false);
const mode = ref("login");

const loginForm = reactive({
  account: "",
  password: ""
});

const registerForm = reactive({
  username: "",
  display_name: "",
  email: "",
  password: ""
});

function nextRoute() {
  const redirect = route.query.redirect;
  if (typeof redirect === "string" && redirect.startsWith("/")) {
    return redirect;
  }
  return "/";
}

async function submitLogin() {
  if (!loginForm.account || !loginForm.password) {
    Message.warning("Please input account and password");
    return;
  }

  loading.value = true;
  try {
    const session = await api.login(loginForm);
    saveAuth(session);
    Message.success(`Welcome back, ${session.user.display_name}`);
    await router.replace(nextRoute());
  } catch (error) {
    Message.error(error.message || "Login failed");
  } finally {
    loading.value = false;
  }
}

async function submitRegister() {
  if (registerForm.username.length < 3 || registerForm.password.length < 6) {
    Message.warning("Username >= 3 and password >= 6");
    return;
  }

  loading.value = true;
  try {
    const session = await api.register(registerForm);
    saveAuth(session);
    Message.success(`Account created: ${session.user.username}`);
    await router.replace(nextRoute());
  } catch (error) {
    Message.error(error.message || "Register failed");
  } finally {
    loading.value = false;
  }
}
</script>
