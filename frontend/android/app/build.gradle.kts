plugins {
    id "com.android.application"
    id "kotlin-android"
    id "dev.flutter.flutter-gradle-plugin"
}

android {
    namespace = "ai.naviable"
    compileSdk = 34

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_11
        targetCompatibility = JavaVersion.VERSION_11
    }

    kotlinOptions {
        jvmTarget = JavaVersion.VERSION_11.toString()
    }

    defaultConfig {
        applicationId = "ai.naviable"
        minSdk = 23
        targetSdk = 34
        versionCode = 1
        versionName = "1.0.0"

        manifestPlaceholders["MAPS_API_KEY"] = (project.findProperty("MAPS_API_KEY") ?: "") as String
    }

    buildTypes {
        release {
            signingConfig = signingConfigs.debug
        }
    }
}

flutter {
    source = "../.."
}
