// Iris Control — one button for the whole household engine (IRIS-CONTROL-001, Doc 2026-10-26).
// Start all / Stop all / Restart / Console / open Rooms & Prime, live status per server,
// and the two-eyes Iris look: blinks, follows your pointer, ring shows health. Motion is cosmetic.
import AppKit

func C(_ h: UInt32, _ a: CGFloat = 1) -> NSColor {
    NSColor(srgbRed: CGFloat((h >> 16) & 255) / 255, green: CGFloat((h >> 8) & 255) / 255, blue: CGFloat(h & 255) / 255, alpha: a)
}
let GOLD = C(0xD8B46A), TEAL = C(0x7FC8C0), RED = C(0xD9534F), BONE = C(0xEFE7D6), INK = C(0x14110c), DEEP = C(0x1b2a2a)

enum Health { case unknown, up, partial, down }

final class EyesView: NSView {
    var gaze = CGPoint.zero          // -1...1 each axis
    var lid: CGFloat = 1             // 1 open, 0.08 shut
    var health: Health = .unknown
    var glow: CGFloat = 0            // 0...1 breathing
    override var isFlipped: Bool { true }
    override func draw(_ dirty: NSRect) {
        guard let g = NSGraphicsContext.current?.cgContext else { return }
        let s = min(bounds.width, bounds.height) / 100
        g.saveGState()
        g.translateBy(x: (bounds.width - 100 * s) / 2, y: (bounds.height - 100 * s) / 2); g.scaleBy(x: s, y: s)
        let ring: NSColor = [.up: TEAL, .partial: GOLD, .down: RED][health] ?? C(0x8a8170)
        // halo
        g.setShadow(offset: .zero, blur: 6 + 6 * glow, color: ring.withAlphaComponent(0.55 + 0.3 * glow).cgColor)
        g.setFillColor(INK.cgColor); g.fillEllipse(in: CGRect(x: 5, y: 5, width: 90, height: 90))
        g.setShadow(offset: .zero, blur: 0, color: nil)
        // face
        let face = CGPath(ellipseIn: CGRect(x: 5, y: 5, width: 90, height: 90), transform: nil)
        g.saveGState(); g.addPath(face); g.clip()
        let grad = CGGradient(colorsSpace: nil, colors: [C(0x3a3326).cgColor, INK.cgColor] as CFArray, locations: [0, 1])!
        g.drawRadialGradient(grad, startCenter: CGPoint(x: 40, y: 35), startRadius: 0, endCenter: CGPoint(x: 40, y: 35), endRadius: 62, options: .drawsAfterEndLocation)
        g.restoreGState()
        g.setStrokeColor(GOLD.cgColor); g.setLineWidth(3); g.addPath(face); g.strokePath()
        g.setStrokeColor(ring.withAlphaComponent(0.85).cgColor); g.setLineWidth(1.2)
        g.strokeEllipse(in: CGRect(x: 9, y: 9, width: 82, height: 82))
        // eyes
        for cx in [34.0, 66.0] as [CGFloat] {
            let ry = 16 * max(0.08, lid)
            let eye = CGRect(x: cx - 13, y: 50 - ry, width: 26, height: 2 * ry)
            g.saveGState()
            g.setFillColor(BONE.cgColor); g.fillEllipse(in: eye)
            g.addEllipse(in: eye); g.clip()
            let px = cx + gaze.x * 4.5, py = 52 + gaze.y * 4.5
            g.setFillColor(TEAL.withAlphaComponent(0.9).cgColor); g.fillEllipse(in: CGRect(x: px - 8, y: py - 8, width: 16, height: 16))
            g.setFillColor(DEEP.cgColor); g.fillEllipse(in: CGRect(x: px - 5.5, y: py - 5.5, width: 11, height: 11))
            g.setFillColor(NSColor.white.cgColor); g.fillEllipse(in: CGRect(x: px - 4, y: py - 5, width: 4, height: 4))
            g.restoreGState()
            if lid < 0.98 {  // upper lid edge
                g.setStrokeColor(C(0x3a3326).cgColor); g.setLineWidth(1.5); g.strokeEllipse(in: eye)
            }
        }
        g.restoreGState()
    }
}

struct Svc { let name: String; let url: String; let core: Bool }
let SERVICES: [Svc] = {
    let f = (Bundle.main.resourcePath ?? "") + "/services.json"
    if let d = FileManager.default.contents(atPath: f), let a = try? JSONSerialization.jsonObject(with: d) as? [[String: Any]] {
        return a.compactMap { x in (x["name"] as? String).flatMap { n in (x["url"] as? String).map { Svc(name: n, url: $0, core: (x["core"] as? Bool) ?? false) } } }
    }
    return [Svc(name: "Iris Prime engine", url: "http://127.0.0.1:8765/api/health", core: true),
            Svc(name: "Prime copy (8772)", url: "http://127.0.0.1:8772/api/health", core: true),
            Svc(name: "Rooms (8773)", url: "http://127.0.0.1:8773/api/health", core: true),
            Svc(name: "Ollama", url: "http://127.0.0.1:11434/api/tags", core: false),
            Svc(name: "EXO", url: "http://127.0.0.1:52415/models", core: false)]
}()

final class App: NSObject, NSApplicationDelegate {
    var win: NSWindow!; let big = EyesView(); let tile = EyesView()
    var dots: [NSTextField] = []; var note = NSTextField(labelWithString: "")
    var up: [Bool?] = Array(repeating: nil, count: SERVICES.count)
    var t0 = Date(), target = CGPoint.zero, nextLook = Date(), busy = false
    let still = NSWorkspace.shared.accessibilityDisplayShouldReduceMotion

    func applicationDidFinishLaunching(_ n: Notification) {
        NSApp.dockTile.contentView = tile; tile.frame = NSRect(x: 0, y: 0, width: 128, height: 128)
        win = NSWindow(contentRect: NSRect(x: 0, y: 0, width: 400, height: 620), styleMask: [.titled, .closable, .miniaturizable, .fullSizeContentView], backing: .buffered, defer: false)
        win.title = "Iris Control"; win.titlebarAppearsTransparent = true; win.isMovableByWindowBackground = true
        win.backgroundColor = C(0x0f0d09); win.appearance = NSAppearance(named: .darkAqua); win.center(); win.isReleasedWhenClosed = false
        let v = win.contentView!
        big.frame = NSRect(x: 120, y: 430, width: 160, height: 160); v.addSubview(big)
        let title = NSTextField(labelWithString: "IRIS"); title.font = NSFont(name: "Didot", size: 30) ?? .systemFont(ofSize: 30, weight: .light)
        title.textColor = GOLD; title.alignment = .center; title.frame = NSRect(x: 0, y: 388, width: 400, height: 38); v.addSubview(title)
        for (i, s) in SERVICES.enumerated() {
            let y = 350 - CGFloat(i) * 24
            let d = NSTextField(labelWithString: "●"); d.textColor = C(0x8a8170); d.frame = NSRect(x: 70, y: y, width: 20, height: 20); v.addSubview(d); dots.append(d)
            let l = NSTextField(labelWithString: s.name); l.textColor = BONE; l.font = .systemFont(ofSize: 13); l.frame = NSRect(x: 92, y: y, width: 260, height: 20); v.addSubview(l)
        }
        let rows: [[(String, Selector)]] = [[("Start all", #selector(startAll)), ("Stop all", #selector(stopAll)), ("Restart", #selector(restart))],
                                            [("Rooms", #selector(rooms)), ("Prime", #selector(prime)), ("Console", #selector(console))]]
        for (r, row) in rows.enumerated() { for (c, b) in row.enumerated() {
            let btn = NSButton(title: b.0, target: self, action: b.1); btn.bezelStyle = .rounded; btn.controlSize = .large
            btn.frame = NSRect(x: 40 + CGFloat(c) * 110, y: 100 - CGFloat(r) * 44, width: 100, height: 34); btn.contentTintColor = GOLD; v.addSubview(btn)
        } }
        // Product launch row (Doc: one button still launches the products). Every Iris product app found, minus Prime and the launchers.
        let products = self.products()
        if !products.isEmpty {
            let cap = NSTextField(labelWithString: "Products"); cap.textColor = C(0x8a8170); cap.font = .systemFont(ofSize: 10); cap.alignment = .center
            cap.frame = NSRect(x: 0, y: 210, width: 400, height: 14); v.addSubview(cap)
            for (i, pr) in products.prefix(6).enumerated() {
                let b = NSButton(title: pr.lastPathComponent.replacingOccurrences(of: ".app", with: ""), target: self, action: #selector(self.openProd(_:)))
                b.bezelStyle = .rounded; b.font = .systemFont(ofSize: 11); b.contentTintColor = TEAL; b.toolTip = pr.path
                b.frame = NSRect(x: 20 + CGFloat(i % 3) * 122, y: 182 - CGFloat(i / 3) * 30, width: 118, height: 26)
                b.identifier = NSUserInterfaceItemIdentifier(pr.path); v.addSubview(b)
            }
        }
        note.textColor = C(0xb7ad98); note.font = .systemFont(ofSize: 11); note.alignment = .center; note.lineBreakMode = .byTruncatingMiddle
        note.frame = NSRect(x: 20, y: 14, width: 360, height: 18); v.addSubview(note)
        win.makeKeyAndOrderFront(nil); NSApp.activate(ignoringOtherApps: true)
        Timer.scheduledTimer(withTimeInterval: 1.0 / 30, repeats: true) { [weak self] _ in self?.frameTick() }
        Timer.scheduledTimer(withTimeInterval: 1.0 / 12, repeats: true) { [weak self] _ in self?.tileTick() }
        Timer.scheduledTimer(withTimeInterval: 4, repeats: true) { [weak self] _ in self?.probe() }
        probe()
    }
    func applicationShouldHandleReopen(_ s: NSApplication, hasVisibleWindows f: Bool) -> Bool { win.makeKeyAndOrderFront(nil); return true }

    func lidNow() -> CGFloat {   // same rhythm as the web assistant: 6.5 s, shut at 95.5 %
        if still { return 1 }
        let p = Date().timeIntervalSince(t0).truncatingRemainder(dividingBy: 6.5) / 6.5
        if p < 0.93 { return 1 }; if p < 0.955 { return 1 - CGFloat((p - 0.93) / 0.025) * 0.92 }
        if p < 0.985 { return 0.08 + CGFloat((p - 0.955) / 0.03) * 0.92 }; return 1
    }
    func gazeToward(_ center: CGPoint) -> CGPoint {
        let m = NSEvent.mouseLocation, dx = m.x - center.x, dy = center.y - m.y, d = max(1, hypot(dx, dy)), k = min(1, d / 220)
        return CGPoint(x: dx / d * k, y: dy / d * k)
    }
    func ease(_ v: EyesView, _ t: CGPoint) { v.gaze = CGPoint(x: v.gaze.x + (t.x - v.gaze.x) * 0.22, y: v.gaze.y + (t.y - v.gaze.y) * 0.22) }
    func frameTick() {
        guard win.isVisible, !win.isMiniaturized else { return }
        let r = win.convertToScreen(big.convert(big.bounds, to: nil))
        ease(big, still ? .zero : gazeToward(CGPoint(x: r.midX, y: r.midY)))
        big.lid = lidNow(); big.glow = still ? 0.5 : CGFloat(0.5 + 0.5 * sin(Date().timeIntervalSince(t0) * 2 * .pi / 3.2)); big.needsDisplay = true
    }
    func tileTick() {   // the Dock icon: idle glances when the pointer is far, tracks it when near the Dock
        let scr = NSScreen.main?.frame ?? .zero, m = NSEvent.mouseLocation
        var t: CGPoint
        if m.y < scr.minY + 140 { t = gazeToward(CGPoint(x: m.x, y: scr.minY + 40)); t.x *= 0.2; t.y = 0.7 }
        else {
            if Date() > nextLook { target = CGPoint(x: .random(in: -0.9...0.9), y: .random(in: -0.6...0.6)); nextLook = Date().addingTimeInterval(.random(in: 1.2...3.5)) }
            t = target
        }
        ease(tile, still ? .zero : t); tile.lid = lidNow(); tile.health = big.health; tile.glow = big.glow
        NSApp.dockTile.display()
    }
    func probe() {
        for (i, s) in SERVICES.enumerated() {
            var rq = URLRequest(url: URL(string: s.url)!); rq.timeoutInterval = 2
            URLSession.shared.dataTask(with: rq) { _, resp, _ in
                let ok = (resp as? HTTPURLResponse) != nil
                DispatchQueue.main.async { self.up[i] = ok; self.dots[i].textColor = ok ? TEAL : RED; self.summarise() }
            }.resume()
        }
    }
    func summarise() {
        let core = SERVICES.indices.filter { SERVICES[$0].core }.map { up[$0] }
        if core.contains(where: { $0 == nil }) { return }
        let n = core.filter { $0 == true }.count
        big.health = n == core.count ? .up : (n == 0 ? .down : .partial)
    }
    func run(_ verb: String, _ say: String) {
        guard !busy else { return }; busy = true; note.stringValue = say + "…"
        let p = Process(); p.executableURL = URL(fileURLWithPath: "/bin/bash")
        p.arguments = [(Bundle.main.resourcePath ?? "") + "/project-iris-launch.sh", verb]
        var env = ProcessInfo.processInfo.environment
        env["PROJECT_IRIS_LABEL"] = "com.hifidecant.selflight.mbp"; env["PROJECT_IRIS_INSTANCE"] = "mbp-hifidecant"; p.environment = env
        let logURL = FileManager.default.homeDirectoryForCurrentUser.appendingPathComponent("Library/Logs/iris-control.log")
        FileManager.default.createFile(atPath: logURL.path, contents: nil, attributes: nil)
        if let h = try? FileHandle(forWritingTo: logURL) { h.seekToEndOfFile(); h.write("\n== \(Date()) \(verb)\n".data(using: .utf8)!); p.standardOutput = h; p.standardError = h }
        p.terminationHandler = { pr in DispatchQueue.main.async {
            self.busy = false; self.note.stringValue = "\(say): " + (pr.terminationStatus == 0 ? "done" : "exit \(pr.terminationStatus) — see ~/Library/Logs/iris-control.log"); self.probe() } }
        do { try p.run() } catch { busy = false; note.stringValue = "could not start: \(error.localizedDescription)" }
    }
    @objc func startAll() { run("start-all", "Starting all") }
    @objc func restart() { run("restart", "Restarting") }
    @objc func console() { run("console", "Opening console") }
    @objc func stopAll() {
        let a = NSAlert(); a.messageText = "Stop all Iris servers?"
        a.informativeText = "Stops the main engine, the units, the self-healers, and the release gate's candidate servers (8769–8775, including Rooms on 8773)."
        a.addButton(withTitle: "Stop all"); a.addButton(withTitle: "Cancel")
        if a.runModal() == .alertFirstButtonReturn { run("kill-all", "Stopping all") }
    }
    func products() -> [URL] {
        let apps = URL(fileURLWithPath: "/Applications")
        let skip = Set(["Iris Prime", "Project Iris", "Project Iris Start All", "Project Iris Kill All", "Project Iris Restart", "Project Iris Console", "Selflight Local", "Selflight MASTER", "Iris Control"])
        let all = (try? FileManager.default.contentsOfDirectory(at: apps, includingPropertiesForKeys: nil)) ?? []
        return all.filter { $0.pathExtension == "app" }
            .filter { $0.deletingPathExtension().lastPathComponent.hasPrefix("Iris ") }
            .filter { !skip.contains($0.deletingPathExtension().lastPathComponent) }
            .sorted { $0.lastPathComponent < $1.lastPathComponent }
    }
    @objc func openProd(_ b: NSButton) { if let p = b.identifier?.rawValue { NSWorkspace.shared.open(URL(fileURLWithPath: p)) } }
    @objc func rooms() { NSWorkspace.shared.open(URL(string: "http://localhost:8773/rooms")!) }
    @objc func prime() { NSWorkspace.shared.open(URL(fileURLWithPath: "/Applications/Iris Prime.app")) }
}

if CommandLine.arguments.count == 3 && CommandLine.arguments[1] == "--icon" {   // build step: render the still icon
    let out = CommandLine.arguments[2]
    for (px, name) in [(16, "16x16"), (32, "16x16@2x"), (32, "32x32"), (64, "32x32@2x"), (128, "128x128"), (256, "128x128@2x"), (256, "256x256"), (512, "256x256@2x"), (512, "512x512"), (1024, "512x512@2x")] {
        let v = EyesView(frame: NSRect(x: 0, y: 0, width: px, height: px)); v.health = .up; v.glow = 0.6; v.gaze = CGPoint(x: 0.25, y: 0.15)
        let rep = v.bitmapImageRepForCachingDisplay(in: v.bounds)!; v.cacheDisplay(in: v.bounds, to: rep)
        try! rep.representation(using: .png, properties: [:])!.write(to: URL(fileURLWithPath: "\(out)/icon_\(name).png"))
    }
    exit(0)
}
let app = NSApplication.shared; let d = App(); app.delegate = d; app.setActivationPolicy(.regular); app.run()
