import UIKit
import Flutter
import GoogleMaps

@UIApplicationMain
@objc class AppDelegate: FlutterAppDelegate {
  override func application(
    _ application: UIApplication,
    didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]?
  ) -> Bool {
    // Provide Google Maps API key (restrict to iOS bundle ID in Google Cloud Console)
    GMSServices.provideAPIKey(
      ProcessInfo.processInfo.environment["MAPS_API_KEY_IOS"] ?? "YOUR_IOS_MAPS_KEY"
    )
    GeneratedPluginRegistrant.register(with: self)
    return super.application(application, didFinishLaunchingWithOptions: launchOptions)
  }
}
