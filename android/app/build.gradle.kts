plugins { id("com.android.application"); id("org.jetbrains.kotlin.android") }
android {
    namespace = "com.u4ar.lingolive"
    compileSdk = 36
    defaultConfig {
        applicationId = "com.u4ar.lingolive"
        minSdk = 26
        targetSdk = 36
        versionCode = 1
        versionName = "1.0"
        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
    }
    signingConfigs { getByName("debug") { storeFile = rootProject.file(".signing/debug.keystore") } }
    buildTypes { getByName("release") { signingConfig = signingConfigs.getByName("debug"); isMinifyEnabled = false } }
    buildFeatures { buildConfig = true }
    compileOptions { sourceCompatibility = JavaVersion.VERSION_17; targetCompatibility = JavaVersion.VERSION_17 }
    sourceSets.getByName("main").assets.srcDir("../../shared")
    sourceSets.getByName("test").resources.srcDir("src/main/assets")
}
kotlin { compilerOptions { jvmTarget.set(org.jetbrains.kotlin.gradle.dsl.JvmTarget.JVM_17) } }
dependencies {
    implementation("androidx.core:core:1.16.0")
    implementation("com.squareup.okhttp3:okhttp:4.12.0")
    implementation("com.google.mlkit:language-id:17.0.6")
    testImplementation("junit:junit:4.13.2")
    testImplementation("org.json:json:20250517")
    androidTestImplementation("androidx.test:runner:1.6.2")
    androidTestImplementation("androidx.test.ext:junit:1.2.1")
    androidTestImplementation("com.squareup.okhttp3:mockwebserver:4.12.0")
}
