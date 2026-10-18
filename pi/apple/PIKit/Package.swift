// swift-tools-version:5.10
import PackageDescription

let package = Package(
    name: "PIKit",
    platforms: [.iOS(.v17), .watchOS(.v10), .visionOS(.v1), .macOS(.v14)],
    products: [
        .library(name: "PIKit", targets: ["PIKit"]),
        .library(name: "PIUI", targets: ["PIUI"]),
    ],
    targets: [
        .target(name: "PIKit"),
        .target(name: "PIUI", dependencies: ["PIKit"]),
        .testTarget(name: "PIKitTests", dependencies: ["PIKit"]),
    ]
)
