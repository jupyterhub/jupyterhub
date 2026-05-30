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
      // Contains - so append hash
      ["jupyter-alex", "jupyter-alex-651dec0a"],
      ["username-servername", "username-servername-9b109a32"],
      // Lowercase
      ["jupyter-Alex", "jupyter-alex-3a1c285c"],
      // Invalid chars
      ["jupyter-üni", "jupyter-ni-a5aaf5dd"],
      ["user@email.com", "user-email-com-0925f997"],
      ["user-_@_emailß.com", "user-email-com-7e3a7efd"],
      ["has.dot", "has-dot-03e27fdf"],
      ["üser", "ser-73506260"],
      // Multiple -
      ["a-b--c-d", "a-b-c-d-ee1e7bc7"],
      // Doesn't start with [a-z]
      ["9z9", "x-9z9-224de202"],
      ["-start", "start-f587e2dc"],
      // Ends with -
      ["endswith-", "endswith-165f1166"],
      // Looks like it has a hash appended but that's irrelevant
      ["start-f587e2dc", "start-f587e2dc-06b9709d"],
      // Length tests
      ["x".repeat(30), "x".repeat(30)],
      ["x".repeat(31), "xxxxxxxxxxxxxxxxxxxxx-0f46e4b0"],
      ["x".repeat(32), "xxxxxxxxxxxxxxxxxxxxx-c62e4615"],
      // Length tests with invalid chars
      ["x".repeat(29) + "-", "xxxxxxxxxxxxxxxxxxxxx-bf57e3d7"],
      ["1234567890".repeat(3), "x-1234567890123456789-f54e5c8f"],
    ];
    testCases.forEach(([input, expected]) => {
      it(`creates a safe slug: ${input}`, () => {
        expect(utils.safe_slug(input)).toBe(expected);
      });
    });
  });
});
