import XCTest

/// Launches the app on Casual View (pointed at a gateway via launch args) and runs Apple's accessibility audit.
final class CasualViewAccessibilityTests: XCTestCase {
    override func setUp() { continueAfterFailure = true }

    private func launch() -> XCUIApplication {
        let app = XCUIApplication()
        let env = ProcessInfo.processInfo.environment
        app.launchArguments = ["-PIGatewayURL", env["PI_TEST_GATEWAY_URL"] ?? "http://127.0.0.1:8784"]
        if let t = env["PI_TEST_TOKEN"], !t.isEmpty { app.launchArguments += ["-PISeedToken", t] }
        app.launch()
        XCTAssertTrue(app.buttons["Talk"].waitForExistence(timeout: 15), "Casual View (Talk button) did not appear")
        _ = app.staticTexts.containing(NSPredicate(format: "label CONTAINS 'Gateway'")).firstMatch.waitForExistence(timeout: 10)
        return app
    }

    func testCasualViewIsLaunchScreen() {
        let app = launch()
        XCTAssertTrue(app.navigationBars["PI"].exists)
        XCTAssertTrue(app.buttons["Talk"].isHittable)
        let shot = XCTAttachment(screenshot: app.screenshot())
        shot.name = "CasualView"
        shot.lifetime = .keepAlways
        add(shot)
    }

    func testCasualViewAccessibilityAudit() throws {
        let app = launch()
        var issues: [String] = []
        try app.performAccessibilityAudit { issue in
            let line = "AUDIT ISSUE [\(issue.auditType)] \(issue.compactDescription) | element: \(issue.element?.debugDescription.prefix(160) ?? "nil")"
            print(line)
            issues.append(line)
            return false // report every issue as a failure; nothing is silenced
        }
        print("AUDIT ISSUE COUNT: \(issues.count)")
    }

    func testCasualViewAccessibilityAuditLargestDynamicType() throws {
        let app = XCUIApplication()
        app.launchArguments = ["-PIGatewayURL", ProcessInfo.processInfo.environment["PI_TEST_GATEWAY_URL"] ?? "http://127.0.0.1:8784",
                               "-UIPreferredContentSizeCategoryName", "UICTContentSizeCategoryAccessibilityXXXL"]
        app.launch()
        XCTAssertTrue(app.buttons["Talk"].waitForExistence(timeout: 15))
        let shot = XCTAttachment(screenshot: app.screenshot())
        shot.name = "CasualView-AXXXL"
        shot.lifetime = .keepAlways
        add(shot)
        try app.performAccessibilityAudit(for: [.dynamicType, .textClipped]) { issue in
            print("AUDIT ISSUE AXXXL [\(issue.auditType)] \(issue.compactDescription)")
            return false
        }
    }

    /// End-to-end through the real gateway: type in Chat, send, go back, Casual View shows the answer.
    func testAskFromChatShowsAnswerOnCasualView() {
        let app = launch()
        let chat = app.buttons["nav.chat"]
        for _ in 0..<6 where !chat.isHittable { app.swipeUp() }
        chat.tap()
        let field = app.textFields["Message PI"].exists ? app.textFields["Message PI"] : app.textViews["Message PI"]
        XCTAssertTrue(field.waitForExistence(timeout: 5))
        field.tap()
        field.typeText("What is the status of PI?")
        app.buttons["Send"].tap()
        let answer = app.staticTexts.containing(NSPredicate(format: "label CONTAINS 'I heard'")).firstMatch
        XCTAssertTrue(answer.waitForExistence(timeout: 30), "no answer in Chat")
        app.navigationBars["Chat"].buttons.element(boundBy: 0).tap()
        XCTAssertTrue(app.navigationBars["PI"].waitForExistence(timeout: 5), "did not return to Casual View")
        for _ in 0..<6 where !app.buttons["Talk"].exists { app.swipeDown() }
        XCTAssertTrue(app.buttons["Talk"].waitForExistence(timeout: 5))
        let latest = app.descendants(matching: .any).matching(NSPredicate(format: "label CONTAINS 'I heard: What is the status of PI?'")).firstMatch
        XCTAssertTrue(latest.waitForExistence(timeout: 5), "Casual View does not show the latest answer")
    }
}
