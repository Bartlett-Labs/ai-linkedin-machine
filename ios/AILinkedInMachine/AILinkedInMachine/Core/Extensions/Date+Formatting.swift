import Foundation

extension Date {
    func shortDisplay() -> String {
        let formatter = DateFormatter()
        formatter.dateFormat = "MMM d h:mm a"
        return formatter.string(from: self)
    }

    func relativeDisplay() -> String {
        let formatter = RelativeDateTimeFormatter()
        formatter.unitsStyle = .abbreviated
        return formatter.localizedString(for: self, relativeTo: .now)
    }

    func timeOnly() -> String {
        let formatter = DateFormatter()
        formatter.dateFormat = "h:mm a"
        return formatter.string(from: self)
    }

    func dateOnly() -> String {
        let formatter = DateFormatter()
        formatter.dateFormat = "MMM d, yyyy"
        return formatter.string(from: self)
    }
}

extension String {
    func toDate() -> Date? {
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        if let date = formatter.date(from: self) { return date }
        formatter.formatOptions = [.withInternetDateTime]
        return formatter.date(from: self)
    }
}
