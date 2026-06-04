define(["share/jupyterhub/static/js/utils"], function (utils) {
  describe("utils.safe_slug", () => {
    it("throws an error for empty strings", () => {
      expect(() => utils.safe_slug("")).toThrowError(
        "Unable to create safe slug for empty string",
      );
    });

    // Keep these in sync with jupyterhub/tests/test_slugs.py::test_safe_slug
    const testCases = [
      // Unchanged
      ["z9", "z9"],
      // Contains -
      ["jupyter-alex", "jupyter-alex"],
      ["username-servername", "username-servername"],
      // Lowercase
      ["jupyter-Alex", "jupyter-alex"],
      // Invalid chars
      ["jupyter-üni", "jupyter-uni"],
      ["user@email.com", "user-email-com"],
      ["user-_@_emailß.com", "user-email-com"],
      ["has.dot", "has-dot"],
      ["üser-🐧½", "user-1-2"],
      // Multiple -
      ["a-b--c-d", "a-b-c-d"],
      // Doesn't start with [a-z]
      ["9z9", "x-9z9"],
      ["-start", "start"],
      // Ends with -
      ["endswith-", "endswith"],
      // Looks like it has a hash appended but that's irrelevant
      ["start-f587e2dc", "start-f587e2dc"],
      // Length tests
      ["x".repeat(30), "x".repeat(30)],
      ["x".repeat(31), "x".repeat(30)],
      ["x".repeat(32), "x".repeat(30)],
      // Length tests with invalid chars
      ["x".repeat(29) + "-", "x".repeat(29)],
      ["1234567890".repeat(3), "x-1234567890123456789012345678"],
    ];
    testCases.forEach(([input, expected]) => {
      it(`creates a safe slug: ${input}`, () => {
        expect(utils.safe_slug(input)).toBe(expected);
      });
    });
  });
});
